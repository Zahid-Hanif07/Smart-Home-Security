"""Private local evidence storage for development deployments.

The API exposes evidence only after JWT validation, home ownership validation,
and confirming that the storage key is referenced by a log for that home.
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np

from app.config.settings import SECURITY_EVIDENCE_DIR, SECURITY_EVIDENCE_RETENTION_DAYS


class EvidenceStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or SECURITY_EVIDENCE_DIR).resolve()

    def save_frame(self, home_id: str, frame: np.ndarray | None) -> str | None:
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return None
        key = f"{uuid4().hex}.jpg"
        home_dir = (self.root / str(home_id)).resolve()
        if self.root not in home_dir.parents:
            return None
        try:
            home_dir.mkdir(parents=True, exist_ok=True)
            ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if not ok:
                return None
            target = home_dir / key
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(encoded.tobytes())
            temporary.replace(target)
            return key
        except OSError:
            return None

    def resolve(self, home_id: str, key: str) -> Path | None:
        if not key or Path(key).name != key or key in {".", ".."}:
            return None
        home_dir = (self.root / str(home_id)).resolve()
        path = (home_dir / key).resolve()
        if self.root not in home_dir.parents or home_dir not in path.parents:
            return None
        return path if path.is_file() else None

    def delete_older_than_retention(self, now: datetime | None = None) -> int:
        """Explicit maintenance hook; not run automatically to avoid data loss."""
        now = now or datetime.now(timezone.utc)
        cutoff = now.timestamp() - timedelta(days=SECURITY_EVIDENCE_RETENTION_DAYS).total_seconds()
        deleted = 0
        if not self.root.exists():
            return deleted
        for path in self.root.glob("*/*.jpg"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
                    deleted += 1
            except OSError:
                continue
        return deleted


evidence_store = EvidenceStore()
