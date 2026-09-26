import os
import unittest
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

app = QApplication.instance() or QApplication([])


class TestDashboardUI(unittest.TestCase):

    def setUp(self):
        self.window = MainWindow()

    def test_window_title(self):
        self.assertEqual(self.window.windowTitle(), "Smart Home Security Dashboard")

    def test_initial_button_states(self):
        self.assertTrue(self.window.btn_start.isEnabled())
        self.assertFalse(self.window.btn_stop.isEnabled())

    def test_badge_updates(self):
        self.window.on_status_updated(motion_detected=True, face_detected=True)
        self.assertEqual(self.window.badge_motion.text(), "MOTION DETECTED")
        self.assertEqual(self.window.badge_face.text(), "FACE DETECTED")

        self.window.on_status_updated(motion_detected=False, face_detected=False)
        self.assertEqual(self.window.badge_motion.text(), "NO MOTION")
        self.assertEqual(self.window.badge_face.text(), "NOT DETECTED")

    def tearDown(self):
        if self.window.camera_worker and self.window.camera_worker.isRunning():
            self.window.camera_worker.stop()
        self.window.close()


if __name__ == "__main__":
    unittest.main()
