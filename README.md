# Smart Home Security and Voice Assistant - FYP

## Phase 4: PySide6 Desktop Security Dashboard UI

This repository contains Step 4 of the **Smart Home Security and Voice Assistant** Final Year Project (FYP).

This step introduces a modern, high-performance desktop GUI dashboard built using **PySide6** (Qt for Python). The dashboard integrates with the underlying `CameraService`, `MotionDetectionService`, and `FaceDetectionService` without interrupting frame processing or freezing the user interface.

---

## Recommended Python Version

* **Python 3.9 or higher** (tested on Python 3.14)

---

## Setup Instructions

### 1. Open Windows PowerShell and Navigate to Project Directory

```powershell
cd "C:\Users\Administrator\.gemini\antigravity-ide\scratch\smart_home_security"
```

### 2. Create Virtual Environment (if not already created)

```powershell
python -m venv .venv
```

### 3. Activate Virtual Environment (Windows PowerShell)

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install Project Requirements

```powershell
pip install -r requirements.txt
```

---

## How to Run the Dashboard

Launch the desktop application using the entry point script:

```powershell
python run.py
```

---

## Key Dashboard Features

* **Live Video Feed**: High-resolution central camera display showing real-time webcam feed annotated with motion highlights and face bounding boxes.
* **Non-Blocking Multithreading**: Utilizes PySide6 `QThread` (`CameraWorker`) to execute camera capture and computer vision processing without UI lag or freezing.
* **Real-time Status Badges**:
  - **Camera**: `ONLINE` / `OFFLINE`
  - **Motion**: `NO MOTION` (Green) / `MOTION DETECTED` (Red)
  - **Face**: `NOT DETECTED` (Muted) / `FACE DETECTED` (Cyan)
  - **Door Lock**: `LOCKED` (Static placeholder for upcoming Arduino hardware phase)
* **Control Buttons**: `[ START CAMERA ]` and `[ STOP CAMERA ]` for starting and gracefully releasing camera resources.
* **Security Event Log**: Time-stamped event log documenting system activity (`System started`, `Camera connected`, `Motion detected`, `Face detected`, etc.).

---

## Project Structure

```text
smart_home_security/
│
├── app/
│   ├── main.py                     # Entry point launching PySide6 QApplication
│   │
│   ├── camera/
│   │   └── camera_service.py       # OpenCV camera management
│   │
│   ├── security/
│   │   ├── security_service.py     # Main security pipeline coordinator
│   │   ├── motion_detection_service.py
│   │   └── face_detection_service.py
│   │
│   ├── ui/
│   │   ├── camera_worker.py        # QThread worker processing video off the main thread
│   │   ├── main_window.py          # PySide6 MainWindow layout, signals & slots
│   │   └── styles.py               # Dark security dashboard QSS stylesheet
│   │
│   └── config/
│       └── settings.py             # Global configuration parameters
│
├── models/
│   └── face_detection_yunet_2023mar.onnx
├── tests/
│   └── test_face_detection.py
├── requirements.txt                # opencv-python, PySide6
├── .gitignore
├── README.md
└── run.py
```

---

## Future Modules Roadmap

1. ✅ **Webcam Foundation (Step 1)**
2. ✅ **Motion Detection (Step 2)**
3. ✅ **Face Detection (Step 3)**
4. ✅ **PySide6 Desktop Dashboard UI (Step 4)**
5. **FaceNet Face Recognition**
6. **Authorized Person Detection**
7. **Unknown Person Screenshot Capture**
8. **Email Alert Notifications**
9. **Security Incident Logging**
10. **Covered-Face / Mask Detection**
11. **Video Freeze Detection**
12. **Loop-Video Detection (Anti-spoofing)**
13. **FastAPI Backend API**
14. **Firebase Integration**
15. **Flutter Mobile Application**
16. **Arduino / Servo Motor Integration**
17. **Voice Assistant**
