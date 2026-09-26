import cv2
import numpy as np
from app.config.settings import (
    FACE_RECOGNITION_THRESHOLD,
    FACE_RECOGNITION_METRIC,
)
from app.security.face_embedding_service import FaceEmbeddingService
from app.security.face_database import FaceDatabase


class FaceRecognitionService:
    """Service class responsible for comparing face embeddings against registered local database entries.

    Features:
    - Generates 128D embeddings for detected face bounding boxes.
    - Evaluates distance/similarity against stored person embeddings using cv2.FaceRecognizerSF.match.
    - Determines identity ('Zahid', 'Amish', etc.) or returns 'Unknown'.
    - Handles empty, corrupt, or updated face databases gracefully.
    """

    def __init__(
        self,
        embedding_service: FaceEmbeddingService = None,
        database: FaceDatabase = None,
        threshold: float = FACE_RECOGNITION_THRESHOLD,
        metric: str = FACE_RECOGNITION_METRIC,
    ):
        self.embedding_service = embedding_service or FaceEmbeddingService()
        self.database = database or FaceDatabase()
        self.threshold = threshold
        self.metric = metric

        # Cached database entries: dict[str, list[np.ndarray]]
        self.registered_people = {}
        self.reload_database()

    def reload_database(self) -> None:
        """Reload registered people and embeddings from the local face database."""
        try:
            self.registered_people = self.database.load_database()
            count = len(self.registered_people)
            print(f"FaceRecognitionService loaded {count} registered person(s).")
        except Exception as e:
            print(f"Error reloading face database in recognition service: {e}")
            self.registered_people = {}

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
        box = face_info.get("box", (0, 0, 0, 0))
        detection_confidence = face_info.get("confidence", 0.0)

        # Default fallback result for unrecognized/empty DB
        unknown_result = {
            "name": "Unknown",
            "matched": False,
            "similarity": 0.0,
            "distance": 1.0,
            "box": box,
            "confidence": detection_confidence,
        }

        if not self.registered_people:
            return unknown_result

        # Generate embedding for detected face
        query_embedding = self.embedding_service.compute_embedding(frame, face_info)
        if query_embedding is None:
            return unknown_result

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
                "similarity": best_similarity,
                "distance": best_distance,
                "box": box,
                "confidence": detection_confidence,
            }
        else:
            return {
                "name": "Unknown",
                "matched": False,
                "similarity": max(0.0, best_similarity),
                "distance": best_distance,
                "box": box,
                "confidence": detection_confidence,
            }

    def recognize_faces(self, frame: np.ndarray, detected_faces: list[dict]) -> list[dict]:
        """Recognize identities for all detected faces in a frame."""
        results = []
        for face_info in detected_faces:
            result = self.recognize_face(frame, face_info)
            results.append(result)
        return results
