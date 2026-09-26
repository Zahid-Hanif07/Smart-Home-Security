import cv2
from app.config.settings import CAMERA_INDEX, WINDOW_NAME, FRAME_DELAY_MS


class CameraService:
    """Service class for accessing webcam, capturing live frames, and managing OpenCV display windows."""

    def __init__(self, camera_index: int = CAMERA_INDEX, window_name: str = WINDOW_NAME):
        self.camera_index = camera_index
        self.window_name = window_name
        self.cap = None

    def initialize_camera(self) -> bool:
        """Initialize the OpenCV VideoCapture object.

        Returns:
            bool: True if camera is successfully opened, False otherwise.
        """
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(
                    "Error: Unable to access camera. "
                    "Please check camera permissions or whether another application is using the camera."
                )
                return False
            return True
        except Exception as e:
            print(f"Error while initializing camera: {e}")
            return False

    def start_stream(self, frame_processor=None) -> None:
        """Start capturing frames continuously from webcam and display in an OpenCV window.

        Args:
            frame_processor (callable, optional): Function that receives a BGR frame and returns processed frame.

        Press 'q' key in the video window to quit.
        """
        if self.cap is None or not self.cap.isOpened():
            if not self.initialize_camera():
                return

        print(f"Camera stream started successfully.")
        print(f"Press 'q' in the '{self.window_name}' window to exit.")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    print("Error: Failed to grab frame from camera. Exiting camera stream.")
                    break

                # Apply frame processing pipeline if provided
                display_frame = frame_processor(frame) if frame_processor else frame

                # Display frame in window
                cv2.imshow(self.window_name, display_frame)

                # Wait for key press (q to quit)
                if cv2.waitKey(FRAME_DELAY_MS) & 0xFF == ord('q'):
                    print("Quit key ('q') pressed. Closing stream...")
                    break
        except Exception as e:
            print(f"Unexpected error during streaming: {e}")
        finally:
            self.stop_stream()

    def stop_stream(self) -> None:
        """Safely release webcam hardware resource and close all OpenCV windows."""
        if self.cap is not None:
            if self.cap.isOpened():
                self.cap.release()
            self.cap = None
            print("Webcam resource released.")
        cv2.destroyAllWindows()
        print("OpenCV windows closed.")
