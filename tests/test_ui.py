import os
import time
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.security.face_occlusion_runtime import (
    STATUS_FAILED,
    STATUS_INVALID,
    STATUS_NO_FACE,
    STATUS_STALE,
    STATUS_UNAVAILABLE,
    FaceOcclusionDiagnostic,
)
from app.security.face_occlusion_service import FaceOcclusionResult

app = QApplication.instance() or QApplication([])


class DiagnosticEmitter(QObject):
    updated = Signal(object)


class TestDashboardUI(unittest.TestCase):

    def setUp(self):
        self.window = MainWindow()

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), "Smart Home Security Dashboard")

    def test_initial_button_states(self):
        self.assertTrue(self.window.btn_start.isEnabled())
        self.assertFalse(self.window.btn_stop.isEnabled())
        self.assertEqual(self.window.btn_pair_camera.text(), "Pair Camera")

    def test_badge_updates(self):
        self.window.on_status_updated(motion_detected=True, face_detected=True)
        self.assertEqual(self.window.badge_motion.text(), "MOTION DETECTED")
        self.assertEqual(self.window.badge_face.text(), "FACE DETECTED")

        self.window.on_status_updated(motion_detected=False, face_detected=False)
        self.assertEqual(self.window.badge_motion.text(), "NO MOTION")
        self.assertEqual(self.window.badge_face.text(), "NOT DETECTED")

    def emit_diagnostic(self, diagnostic):
        emitter = DiagnosticEmitter()
        emitter.updated.connect(self.window.on_face_occlusion_updated)
        emitter.updated.emit(diagnostic)
        app.processEvents()

    def test_face_occ_valid_signal_updates_diagnostic_only(self):
        original_identity = self.window.badge_identity.text()
        original_security = self.window.badge_status.text()
        diagnostic = FaceOcclusionDiagnostic(
            frame_sequence=30,
            face_index=1,
            box=(10, 10, 40, 40),
            submitted_at=time.monotonic() - 0.1,
            completed_at=time.monotonic() - 0.05,
            status="success",
            reason="segmentation_completed",
            result=FaceOcclusionResult(
                state="segmentation_available",
                reason="segmentation_completed",
                mode="direct_crop",
                visible_ratio=0.75,
                inference_ms=12.5,
            ),
        )

        self.emit_diagnostic(diagnostic)

        self.assertEqual(self.window.badge_face_occ.text(), "ANALYZED")
        self.assertIn("Face 1", self.window.lbl_face_occ_detail.text())
        self.assertIn("Visible 0.750", self.window.lbl_face_occ_detail.text())
        self.assertIn("Inference 12.5 ms", self.window.lbl_face_occ_detail.text())
        self.assertEqual(self.window.badge_identity.text(), original_identity)
        self.assertEqual(self.window.badge_status.text(), original_security)

    def test_face_occ_failure_states_are_displayed(self):
        for status, expected in (
            (STATUS_UNAVAILABLE, "UNAVAILABLE"),
            (STATUS_INVALID, "UNCERTAIN"),
            (STATUS_FAILED, "FAILED"),
            (STATUS_NO_FACE, "NO FACE"),
            (STATUS_STALE, "STALE"),
        ):
            diagnostic = FaceOcclusionDiagnostic(
                frame_sequence=30,
                face_index=-1,
                box=(0, 0, 0, 0),
                submitted_at=time.monotonic(),
                completed_at=time.monotonic(),
                status=status,
                reason="synthetic_status",
            )
            self.emit_diagnostic(diagnostic)
            self.assertEqual(self.window.badge_face_occ.text(), expected)
            self.assertIn("synthetic_status", self.window.lbl_face_occ_detail.text())

    def test_stale_older_result_does_not_overwrite_newer_result(self):
        newer = FaceOcclusionDiagnostic(
            frame_sequence=45,
            face_index=0,
            box=(1, 1, 20, 20),
            submitted_at=time.monotonic(),
            completed_at=time.monotonic(),
            status="success",
            reason="newer",
            result=FaceOcclusionResult(
                state="segmentation_available",
                reason="newer",
                mode="direct_crop",
                visible_ratio=0.8,
                inference_ms=10.0,
            ),
        )
        older = FaceOcclusionDiagnostic(
            frame_sequence=30,
            face_index=0,
            box=(1, 1, 20, 20),
            submitted_at=time.monotonic(),
            completed_at=time.monotonic(),
            status=STATUS_FAILED,
            reason="older",
        )

        self.emit_diagnostic(newer)
        self.emit_diagnostic(older)

        self.assertEqual(self.window.badge_face_occ.text(), "ANALYZED")
        self.assertIn("Visible 0.800", self.window.lbl_face_occ_detail.text())

    def test_missing_timestamp_does_not_crash_diagnostic_display(self):
        diagnostic = FaceOcclusionDiagnostic(
            frame_sequence=60,
            face_index=0,
            box=(1, 1, 20, 20),
            submitted_at=None,
            completed_at=None,
            status="success",
            reason="timestamp_missing",
            result=FaceOcclusionResult(
                state="segmentation_available",
                reason="timestamp_missing",
                mode="direct_crop",
                visible_ratio=0.5,
                inference_ms=10.0,
            ),
        )

        self.emit_diagnostic(diagnostic)

        self.assertEqual(self.window.badge_face_occ.text(), "ANALYZED")
        self.assertIn("Age unavailable", self.window.lbl_face_occ_detail.text())

    def tearDown(self):
        if self.window.camera_worker and self.window.camera_worker.isRunning():
            self.window.camera_worker.stop()
        self.window.close()


if __name__ == "__main__":
    unittest.main()
