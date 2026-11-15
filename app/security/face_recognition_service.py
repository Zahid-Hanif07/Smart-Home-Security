import os
import time
import cv2
import numpy as np
from typing import Any, Optional
from app.config.settings import (
    FACE_RECOGNITION_THRESHOLD,
    FACE_RECOGNITION_METRIC,
    SECURITY_HOME_ID,
    ALLOW_LOCAL_FACE_DATABASE,
)
from app.config.backend_settings import settings as backend_settings
from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_database import FaceDatabase
from app.services.api_client import APIClient
from app.security.face_security_service import FaceSecurityService

_UNSET_HOME_ID = object()


class FaceRecognitionService:
    """Service class responsible for comparing face embeddings against registered database entries.

    Features:
    - Generates 128D embeddings for detected face bounding boxes.
    - Loads embeddings only for the configured home; optional local data is explicit development-only mode.
    - Evaluates distance/similarity against stored person embeddings using cv2.FaceRecognizerSF.match.
    - Determines identity ('Zahid', 'Amish', etc.) or returns 'Unknown'.
    """

    def __init__(
        self,
        embedding_service: FaceEmbeddingService = None,
        database: FaceDatabase = None,
        threshold: float = FACE_RECOGNITION_THRESHOLD,
        metric: str = FACE_RECOGNITION_METRIC,
        home_id: Any = _UNSET_HOME_ID,
        allow_local_database: Optional[bool] = None,
    ):
        self.embedding_service = embedding_service or FaceEmbeddingService()
        self.database = database or FaceDatabase()
        self.face_security = FaceSecurityService()
        self.threshold = threshold
        self.metric = metric
        self.home_id = (
            os.getenv("SECURITY_HOME_ID") or SECURITY_HOME_ID
            if home_id is _UNSET_HOME_ID
            else home_id
        )
        self.allow_local_database = ALLOW_LOCAL_FACE_DATABASE if allow_local_database is None else allow_local_database

        # Cached database entries: dict[str, list[np.ndarray]]
        self.registered_people = {}
        self._loaded_from_remote = False
        self.data_source = "unavailable"
        self.database_error = None
        self._last_local_database_check = 0.0
        self._local_database_mtime = None
        self.reload_database()

    def reload_database(self, home_id: Any = _UNSET_HOME_ID) -> None:
        """Reload registered people and 128D embeddings from FastAPI/Supabase face_records (or local DB fallback)."""
        if home_id is not _UNSET_HOME_ID:
            self.home_id = home_id
        target_home_id = self.home_id
        self.registered_people = {}
        self._loaded_from_remote = False
        self.data_source = "unavailable"
        self.database_error = None
        people = {}

        if target_home_id:
            try:
                auth_token = (
                    os.getenv("SUPABASE_ACCESS_TOKEN")
                    or os.getenv("AUTH_TOKEN")
                    or backend_settings.SUPABASE_ACCESS_TOKEN
                )
                client = APIClient(auth_token=auth_token)
                records = client.get_home_face_records(target_home_id)
                if records is not None:
                    for rec in records:
                        name = rec.get("member_name")
                        emb_raw = rec.get("embedding")
                        if name and emb_raw and isinstance(emb_raw, list) and len(emb_raw) == 128:
                            emb_np = np.array(emb_raw, dtype=np.float32)
                            if name not in people:
                                people[name] = []
                            people[name].append(emb_np)
                    if people:
                        self.registered_people = people
                        self._loaded_from_remote = True
                        self.data_source = "remote"
                        self._remember_local_database_mtime()
                        return
                    if len(records) == 0:
                        self.data_source = "remote"
                    else:
                        self.database_error = "The selected home returned face records, but none had valid 128D embeddings."
                    if not self.allow_local_database:
                        self._remember_local_database_mtime()
                        return
                else:
                    self.database_error = "Face records could not be loaded from the authenticated API."
            except Exception as e:
                self.database_error = f"Could not load selected-home face records: {e}"
        else:
            self.database_error = "No paired device home has been resolved."

        # Local data is opt-in for isolated development or tests when remote records are not available.
        if self.allow_local_database and (not target_home_id or not self._loaded_from_remote):
            try:
                local_data = self.database.load_database()
                if local_data:
                    self.registered_people = local_data
                    self.data_source = "local_development"
                    self.database_error = None
                elif not self.registered_people:
                    self.data_source = "local_development"
                self._remember_local_database_mtime()
            except Exception as e:
                self.database_error = f"Could not load local development face records: {e}"

    def _remember_local_database_mtime(self) -> None:
        try:
            self._local_database_mtime = os.path.getmtime(self.database.db_file)
        except OSError:
            self._local_database_mtime = None

    def _refresh_local_database_if_changed(self) -> None:
        """Pick up mobile enrollments written by the local API while the camera runs."""
        if self.data_source != "local_development":
            return
        now = time.monotonic()
        if now - self._last_local_database_check < 2.0:
            return
        self._last_local_database_check = now
        try:
            modified = os.path.getmtime(self.database.db_file)
        except OSError:
            return
        if modified == self._local_database_mtime:
            return
        self.reload_database()

    def recognize_face(self, frame: np.ndarray, face_info: dict) -> dict:
        """Recognize identity for a single detected face.

        Args:
            frame (np.ndarray): Full BGR image frame.
            face_info (dict): Face detection result with 'box', 'confidence', and optional 'raw'.

        Returns:
            dict: Recognition result:
                {
                    "name": str,         # Registered person name or "Unknown"
                    "matched": bool,     # True if match found above threshold
                    "similarity": float, # Cosine similarity score
                    "distance": float,   # Distance metric
                    "box": tuple         # (x, y, w, h)
                }
        """
        self._refresh_local_database_if_changed()
        box = face_info.get("box", (0, 0, 0, 0))
        detection_confidence = face_info.get("confidence", 0.0)

        # Default fallback result for unrecognized/empty DB
        unknown_result = {
            "name": "Unknown",
            "matched": False,
            "decision": "unverified",
            "similarity": 0.0,
            "distance": 1.0,
            "box": box,
            "confidence": detection_confidence,
            "reason": self.database_error or "No face database records are available for the selected home.",
        }

        quality = self.face_security.evaluate(frame, face_info)
        unknown_result.update(quality)
        if quality["quality"] != "usable":
            unknown_result["reason"] = quality["reason"]
            return unknown_result

        if self.data_source == "unavailable":
            return unknown_result

        # Generate embedding for detected face
        query_embedding = self.embedding_service.compute_embedding(frame, face_info)
        if query_embedding is None:
            unknown_result["reason"] = "embedding_extraction_failed"
            return unknown_result

        if not self.registered_people:
            return {
                **unknown_result,
                "decision": "unknown_identity",
                "reason": "The selected home has no valid enrolled face records.",
                **quality,
            }

        best_name = "Unknown"
        best_similarity = -1.0
        best_distance = 999.0
        is_matched = False

        # Compare against all registered people and their stored sample embeddings
        for name, embeddings_list in self.registered_people.items():
            for stored_emb in embeddings_list:
                if stored_emb is None or len(stored_emb) != len(query_embedding):
                    continue

                if self.metric == "cosine":
                    # cv2.FaceRecognizerSF_FR_COSINE returns Cosine Similarity [-1, 1]
                    # Higher similarity score means closer match
                    if self.embedding_service.recognizer:
                        sim = float(
                            self.embedding_service.recognizer.match(
                                query_embedding,
                                stored_emb,
                                cv2.FaceRecognizerSF_FR_COSINE,
                            )
                        )
                    else:
                        # Manual fallback cosine calculation
                        norm_q = np.linalg.norm(query_embedding)
                        norm_s = np.linalg.norm(stored_emb)
                        sim = (
                            float(np.dot(query_embedding, stored_emb) / (norm_q * norm_s))
                            if norm_q * norm_s > 0
                            else 0.0
                        )

                    dist = max(0.0, 1.0 - sim)

                    if sim > best_similarity:
                        best_similarity = sim
                        best_distance = dist
                        if sim >= self.threshold:
                            best_name = name
                            is_matched = True

                else:
                    # L2 Norm metric (lower distance is better)
                    if self.embedding_service.recognizer:
                        dist = float(
                            self.embedding_service.recognizer.match(
                                query_embedding,
                                stored_emb,
                                cv2.FaceRecognizerSF_FR_NORM_L2,
                            )
                        )
                    else:
                        dist = float(np.linalg.norm(query_embedding - stored_emb))

                    sim = max(0.0, 1.0 - (dist / 2.0))

                    if dist < best_distance:
                        best_distance = dist
                        best_similarity = sim
                        if dist <= self.threshold:
                            best_name = name
                            is_matched = True

        if is_matched:
            return {
                "name": best_name,
                "matched": True,
                "decision": "authorized_identity_match",
                "similarity": best_similarity,
                "distance": best_distance,
                "box": box,
                "confidence": detection_confidence,
                "reason": "Matched a stored face embedding for the selected home; liveness remains unverified.",
                **quality,
            }
        else:
            return {
                "name": "Unknown",
                "matched": False,
                "decision": "unknown_identity",
                "similarity": max(0.0, best_similarity),
                "distance": best_distance,
                "box": box,
                "confidence": detection_confidence,
                "reason": "No stored face embedding met the configured match threshold.",
                **quality,
            }

    def recognize_faces(self, frame: np.ndarray, detected_faces: list[dict]) -> list[dict]:
        """Recognize identities for all detected faces in a frame."""
        results = []
        for face_info in detected_faces:
            result = self.recognize_face(frame, face_info)
            results.append(result)
        return results
