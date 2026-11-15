"""Conservative image-quality gate and explicit unavailable-liveness status.

There is no mask/occlusion or presentation-attack model in the shipped project.
This module deliberately does not infer a mask or a live person from identity.
"""

from typing import Any

import cv2
import numpy as np
from app.config.settings import FACE_QUALITY_MINIMUM_WIDTH, FACE_QUALITY_MINIMUM_SHARPNESS


class FaceSecurityService:
    def __init__(
        self,
        minimum_face_width: int = FACE_QUALITY_MINIMUM_WIDTH,
        minimum_sharpness: float = FACE_QUALITY_MINIMUM_SHARPNESS,
    ) -> None:
        self.minimum_face_width = minimum_face_width
        self.minimum_sharpness = minimum_sharpness

    def evaluate(self, frame: np.ndarray, face_info: dict[str, Any]) -> dict[str, Any]:
        box = face_info.get("box") or (0, 0, 0, 0)
        x, y, width, height = (int(value) for value in box)
        if frame is None or frame.size == 0 or width <= 0 or height <= 0:
            return {"quality": "uncertain", "reason": "invalid_face_crop", "liveness": "unverified"}
        if width < self.minimum_face_width or height < self.minimum_face_width:
            return {"quality": "uncertain", "reason": "face_too_small", "liveness": "unverified"}
        fh, fw = frame.shape[:2]
        x1, y1 = max(0, x), max(0, y)
        x2, y2 = min(fw, x + width), min(fh, y + height)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return {"quality": "uncertain", "reason": "invalid_face_crop", "liveness": "unverified"}
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if sharpness < self.minimum_sharpness:
            return {
                "quality": "uncertain",
                "reason": "face_image_blurred",
                "sharpness": sharpness,
                "occlusion": "uncertain",
                "mask": "unavailable",
                "liveness": "unverified",
            }
        return {
            "quality": "usable",
            "reason": "image_quality_passed_basic_checks",
            "sharpness": sharpness,
            "occlusion": "unverified",
            "mask": "unavailable",
            "liveness": "unverified",
        }
