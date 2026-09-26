import cv2
import numpy as np
from app.config.settings import (
    GAUSSIAN_BLUR_KERNEL,
    DELTA_THRESHOLD,
    MIN_MOTION_AREA,
    ACCUMULATION_WEIGHT,
)


class MotionDetectionService:
    """Service for detecting motion in camera frames using lightweight classical computer vision.

    Technique:
    - Grayscale conversion & Gaussian Blur noise reduction.
    - Accumulated weighted running average for adaptive background modeling.
    - Frame differencing, binary thresholding, and contour area filtering.
    """

    def __init__(
        self,
        blur_kernel=GAUSSIAN_BLUR_KERNEL,
        delta_threshold=DELTA_THRESHOLD,
        min_motion_area=MIN_MOTION_AREA,
        accumulation_weight=ACCUMULATION_WEIGHT,
    ):
        self.blur_kernel = blur_kernel
        self.delta_threshold = delta_threshold
        self.min_motion_area = min_motion_area
        self.accumulation_weight = accumulation_weight
        self.avg_frame = None

    def process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, bool, float]:
        """Process a video frame to detect motion and draw visual overlays.

        Args:
            frame (np.ndarray): Original BGR frame from webcam.

        Returns:
            tuple: (annotated_frame, motion_detected, total_motion_area)
                - annotated_frame: Frame with motion bounding boxes & status text overlay.
                - motion_detected: True if total motion area exceeds min_motion_area.
                - total_motion_area: Sum of motion contour areas in pixels.
        """
        if frame is None:
            return frame, False, 0.0

        annotated_frame = frame.copy()

        # 1. Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 2. Gaussian blur to smooth out camera sensor noise
        gray_blurred = cv2.GaussianBlur(gray, self.blur_kernel, 0)

        # 3. Initialize background model on first frame
        if self.avg_frame is None:
            self.avg_frame = gray_blurred.astype("float")
            self._draw_overlay(annotated_frame, motion_detected=False, motion_score=0.0)
            return annotated_frame, False, 0.0

        # 4. Accumulate running average for background adaptiveness
        cv2.accumulateWeighted(gray_blurred, self.avg_frame, self.accumulation_weight)

        # 5. Compute absolute difference between current frame and running background
        frame_delta = cv2.absdiff(gray_blurred, cv2.convertScaleAbs(self.avg_frame))

        # 6. Apply thresholding to isolate movement pixels
        _, thresh = cv2.threshold(frame_delta, self.delta_threshold, 255, cv2.THRESH_BINARY)

        # 7. Dilate thresholded image to connect region gaps
        thresh = cv2.dilate(thresh, None, iterations=2)

        # 8. Find contours of changed pixel regions
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        total_motion_area = 0.0

        # 9. Evaluate contours against minimum motion threshold
        for contour in contours:
            area = cv2.contourArea(contour)
            if area >= self.min_motion_area:
                motion_detected = True
                total_motion_area += area

                # Draw red bounding rectangle around detected motion area
                (x, y, w, h) = cv2.boundingRect(contour)
                cv2.rectangle(annotated_frame, (x, y), (x + w, y + h), (0, 0, 255), 2)

        # 10. Draw visual feedback on frame
        self._draw_overlay(annotated_frame, motion_detected, total_motion_area)

        return annotated_frame, motion_detected, total_motion_area

    def _draw_overlay(self, frame: np.ndarray, motion_detected: bool, motion_score: float) -> None:
        """Draw status banner and motion metric text overlay on image."""
        status_text = "MOTION DETECTED" if motion_detected else "NO MOTION"
        status_color = (0, 0, 255) if motion_detected else (0, 255, 0)  # Red = Motion, Green = Safe

        # Draw main status label
        cv2.putText(
            frame,
            f"Status: {status_text}",
            (10, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            status_color,
            2,
            cv2.LINE_AA,
        )

        # Draw debugging motion score (pixel area)
        cv2.putText(
            frame,
            f"Motion Area: {int(motion_score)} px",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )

    def reset_background(self) -> None:
        """Reset background model to force recalculation on next frame."""
        self.avg_frame = None
