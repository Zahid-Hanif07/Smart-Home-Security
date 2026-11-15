# Phase 9.1 — Desktop Camera Worker Lifecycle Test Matrix

Status: **PASS**

## Scope and safety

This phase used deterministic fakes for `cv2.VideoCapture`, `SecurityService`,
`FramePublisher`, the FaceOcc runtime, and the FaceOcc diagnostic publisher.
No physical webcam, desktop application, FastAPI server, Flutter application,
Supabase connection, model download, or external network request was used.

The repository was already substantially modified before this phase. Those
changes were preserved; no reset, clean, checkout, stash, or overwrite was
performed.

## Files inspected

- `app/ui/camera_worker.py`
- `app/ui/main_window.py`
- `app/streaming/frame_publisher.py`
- `app/security/security_service.py`
- `app/security/face_occlusion_runtime.py`
- `app/security/face_occlusion_service.py`
- `app/services/face_occlusion_diagnostic_publisher.py`
- `tests/test_paired_home_identity.py`
- `tests/test_device_pairing_client.py`
- `tests/test_stream_integrity.py`
- `tests/test_face_occlusion_service.py`
- `tests/test_face_occlusion_runtime.py`
- `tests/test_face_occlusion_diagnostic_publisher.py`
- `tests/test_ui.py`

## Files changed

1. `tests/test_camera_worker_lifecycle.py`
   - Added five focused fake-based lifecycle tests.
2. `app/ui/camera_worker.py`
   - Added `self.frame_publisher.stop()` to the existing `run()` `finally`
     cleanup block.
3. `docs/phase_9/PHASE_9_1_DESKTOP_CAMERA_LIFECYCLE_TESTS.md`
   - Added this report.

The `camera_worker.py` file contained unrelated pre-existing worktree changes;
this phase changed only the missing cleanup call described above.

## Test matrix

| Case | Result | Evidence |
|---|---|---|
| Successful startup and frame processing | PASS | Worker reads a mocked frame and releases all resources |
| Camera open failure | PASS | Error signal emitted, capture released, frame publisher stopped |
| Camera read failure | PASS | Error path releases capture, FaceOcc runtime, diagnostic publisher, and frame publisher |
| Unexpected processing exception | PASS | Error signal emitted and all cleanup paths execute |
| Repeated sequential start/stop | PASS | Two independent workers release their own resources |
| Publisher shutdown on unexpected worker termination | PASS | Regression assertion verifies `FramePublisher.stop()` in `run()` cleanup |
| FaceOcc resource cleanup | PASS | Runtime and diagnostic publisher stop calls verified |

## Proven defect and correction

Before the correction, `CameraWorker.run()` stopped the FaceOcc runtime and
diagnostic publisher in its `finally` block but did not stop `FramePublisher`.
`CameraWorker.stop()` did stop it, so explicit shutdown was covered while
unexpected processing/read termination could leave the frame-publisher worker
running.

The smallest safe correction was one call in the existing `finally` block:

```python
self.frame_publisher.stop()
```

This does not alter camera capture, YuNet, SFace, identity decisions,
authentication, MJPEG contracts, security events, or FaceOcc inference.

## Commands and actual results

### Compilation

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m py_compile tests\test_camera_worker_lifecycle.py app\ui\camera_worker.py
```

Result: completed successfully.

### New lifecycle matrix

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m pytest -q tests\test_camera_worker_lifecycle.py
```

Result: **5 passed, 1 warning** in 2.81 seconds.

### Focused neighboring regression suite

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m pytest -q tests\test_camera_worker_lifecycle.py tests\test_stream_integrity.py tests\test_face_occlusion_service.py tests\test_face_occlusion_runtime.py tests\test_face_occlusion_diagnostic_publisher.py tests\test_device_pairing_client.py tests\test_paired_home_identity.py
```

Result: **69 passed, 1 warning** in 4.54 seconds.

### UI regression suite

```powershell
$env:TEST_ISOLATED_MODE='1'
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q tests\test_ui.py
```

Result: **7 passed, 1 warning** in 3.76 seconds.

The recurring warning was a local pytest cache warning: pytest could not create
`D:\.pytest_cache\v\cache` because a path already existed (`WinError 183`). It
did not fail or alter the tests.

### Diff validation

```powershell
git diff --check -- app/ui/camera_worker.py tests/test_camera_worker_lifecycle.py
```

Result: no whitespace errors. Git printed its normal line-ending warning for
the already modified `camera_worker.py` file.

## Counts

- Passed: 81 test executions across the three commands (5 + 69 + 7; the
  neighboring command includes the five lifecycle tests again).
- Failed: 0.
- Skipped: 0.
- Not run: full project suite, physical-camera validation, live backend/mobile
  integration, and unrelated feature tests.
- Warnings: 3 command-level pytest cache warnings, one per invocation.

## Resource and behavior conclusions

- `FramePublisher` now stops on normal `run()` completion, read failure, and
  unexpected processing exceptions.
- FaceOcc runtime and diagnostic publisher stop on the normal `finally` path.
- Camera capture release is verified on open failure, read failure, and
  processing exception.
- Repeated sequential worker cleanup is safe under the tested fake conditions.
- `CameraWorker.stop()` remains the explicit shutdown path and was not
  redesigned.
- The tests do not establish behavior of a real camera, real network, or
  long-running Qt thread scheduling.

## Remaining risks and next phase

The lifecycle matrix does not prove physical-camera stability, backend
availability, or production shutdown timing. A later authorized phase can
perform controlled live-camera testing; it should remain separate from this
offline regression work.

Do not proceed to voice-assistant or mobile-lifecycle work based on this report
alone. The desktop cleanup defect is corrected and covered, but live hardware
and full-suite verification remain separate tasks.
