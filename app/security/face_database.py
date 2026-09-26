import os
import json
import shutil
import cv2
import numpy as np
from app.config.settings import FACE_DATABASE_DIR, FACE_DATABASE_FILE, FACES_DIR


class FaceDatabase:
    """Repository class managing local persistent face embeddings and registration samples.

    Storage Layout:
    data/
    ├── faces/
    │   └── <PersonName>/
    │       ├── sample_01.jpg
    │       └── sample_02.jpg
    └── face_database/
        └── embeddings.json
    """

    def __init__(
        self,
        db_file: str = FACE_DATABASE_FILE,
        db_dir: str = FACE_DATABASE_DIR,
        faces_dir: str = FACES_DIR,
    ):
        self.db_file = db_file
        self.db_dir = db_dir
        self.faces_dir = faces_dir

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Create storage directories if they do not exist."""
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.faces_dir, exist_ok=True)

    def load_database(self) -> dict[str, list[np.ndarray]]:
        """Load registered people and their embedding vectors from local JSON database.

        Returns:
            dict[str, list[np.ndarray]]: Mapping of person name to list of 128D numpy embeddings.
        """
        if not os.path.exists(self.db_file):
            return {}

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            database = {}
            for name, record in data.items():
                if "embeddings" in record and isinstance(record["embeddings"], list):
                    embeddings_list = []
                    for emb in record["embeddings"]:
                        embeddings_list.append(np.array(emb, dtype=np.float32))
                    if embeddings_list:
                        database[name] = embeddings_list

            return database
        except Exception as e:
            print(f"Error loading face database from {self.db_file}: {e}")
            return {}

    def save_person(
        self,
        name: str,
        embeddings: list[np.ndarray],
        face_images: list[np.ndarray] = None,
    ) -> bool:
        """Save a new or updated person with multiple embedding vectors and optional face sample images.

        Args:
            name (str): Unique name identifier of person.
            embeddings (list[np.ndarray]): List of 128D numpy float32 embedding vectors.
            face_images (list[np.ndarray], optional): BGR cropped face image samples.

        Returns:
            bool: True if save succeeded, False otherwise.
        """
        if not name or not name.strip() or not embeddings:
            print("Error: Invalid name or empty embeddings list provided.")
            return False

        clean_name = name.strip()

        try:
            # 1. Load existing database content
            current_data = {}
            if os.path.exists(self.db_file):
                try:
                    with open(self.db_file, "r", encoding="utf-8") as f:
                        current_data = json.load(f)
                except Exception:
                    current_data = {}

            # 2. Convert numpy embeddings to Python lists for JSON serialization
            serialized_embeddings = [emb.tolist() for emb in embeddings]

            current_data[clean_name] = {
                "embeddings": serialized_embeddings,
                "sample_count": len(serialized_embeddings),
            }

            # 3. Write updated embeddings.json
            with open(self.db_file, "w", encoding="utf-8") as f:
                json.dump(current_data, f, indent=4)

            # 4. Save face images to data/faces/<PersonName>/
            if face_images:
                person_dir = os.path.join(self.faces_dir, clean_name)
                os.makedirs(person_dir, exist_ok=True)
                for idx, img in enumerate(face_images, start=1):
                    if img is not None and img.size > 0:
                        img_path = os.path.join(person_dir, f"sample_{idx:02d}.jpg")
                        cv2.imwrite(img_path, img)

            print(f"Person '{clean_name}' successfully registered with {len(embeddings)} samples.")
            return True
        except Exception as e:
            print(f"Error saving person '{clean_name}' to face database: {e}")
            return False

    def remove_person(self, name: str) -> bool:
        """Remove a person and their stored face samples from the database.

        Args:
            name (str): Name of person to remove.

        Returns:
            bool: True if removed successfully.
        """
        if not os.path.exists(self.db_file):
            return False

        try:
            with open(self.db_file, "r", encoding="utf-8") as f:
                current_data = json.load(f)

            if name in current_data:
                del current_data[name]
                with open(self.db_file, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, indent=4)

            # Remove image directory if present
            person_dir = os.path.join(self.faces_dir, name)
            if os.path.exists(person_dir):
                shutil.rmtree(person_dir, ignore_errors=True)

            print(f"Person '{name}' removed from face database.")
            return True
        except Exception as e:
            print(f"Error removing person '{name}': {e}")
            return False

    def get_registered_names(self) -> list[str]:
        """Return list of names of all registered individuals."""
        db = self.load_database()
        return list(db.keys())

    def has_registered_faces(self) -> bool:
        """Check if database contains any registered faces."""
        return len(self.get_registered_names()) > 0

    def is_empty(self) -> bool:
        """Check if face database is empty or missing."""
        return not self.has_registered_faces()
