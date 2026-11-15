# Phase 9.2 — Desktop and Backend Stability Baseline

Status: **PASS**

## Scope and safety

This was a read-only inspection and offline test baseline. No application
source, configuration, credential, model, database, or runtime behavior was
changed. No physical webcam, FastAPI server, Flutter application, Supabase
connection, or external service was started.

All tests used the project virtual environment and isolated test mode where
appropriate:

```powershell
$env:TEST_ISOLATED_MODE='1'
```

## Worktree status

The worktree was already heavily modified before this phase, including desktop,
backend, Flutter, model, test, environment, and documentation files. Existing
changes and untracked files were preserved. No reset, clean, stash, checkout,
or overwrite operation was used.

The only file created by this phase is:

- `docs/phase_9/PHASE_9_2_DESKTOP_BACKEND_STABILITY_BASELINE.md`

## Phase 9.1 verification

Inspected:

- `app/ui/camera_worker.py`
- `tests/test_camera_worker_lifecycle.py`
- `docs/phase_9/PHASE_9_1_DESKTOP_CAMERA_LIFECYCLE_TESTS.md`

The Phase 9.1 correction remains present:

```python
self.frame_publisher.stop()
```

It appears in the camera-open failure path, the `run()` `finally` cleanup path,
and the explicit `stop()` path. The lifecycle regression test also remains
present. The other changes visible in `camera_worker.py` predate this phase and
were not altered.

## Test inventory

### Desktop and streaming

- `tests/test_camera_worker_lifecycle.py` — mocked CameraWorker startup,
  failure, exception, and cleanup matrix.
- `tests/test_stream_integrity.py` — stream integrity behavior.
- `tests/test_step8.py` — FrameManager and MJPEG helper/endpoint checks.
- `tests/test_ui.py` — offscreen PySide6 dashboard checks.
- `tests/test_paired_home_identity.py` — CameraWorker and paired-home identity
  behavior.
- `tests/test_video_device_sessions.py` — FramePublisher/device-session frame
  publishing behavior.
- `tests/test_device_pairing_client.py` — desktop pairing client and
  FramePublisher credential loading.

### Device pairing, authentication, and authorization

- `tests/test_pairing.py`
- `tests/test_device_auth.py`
- `tests/test_device_credential_store.py`
- `tests/test_device_session_exchange.py`
- `tests/test_device_session_token.py`
- `tests/test_security_authorization.py`

### Video and FaceOcc

- `tests/test_video_routes.py`
- `tests/test_face_occlusion_service.py`
- `tests/test_face_occlusion_runtime.py`
- `tests/test_face_occlusion_diagnostic_publisher.py`
- `tests/test_face_occlusion_api.py`

### Security, detection, repositories, and API routes

- `tests/test_face_detection.py`
- `tests/test_step5.py` — embedding, face database, recognition, and security
  pipeline checks.
- `tests/test_step7.py` — security events, logs, alerts, cooldowns, and
  unavailable-backend handling.
- `tests/test_backend.py` — health, authentication, homes, members, faces,
  devices, logs, alerts, and cross-user isolation.
- `tests/test_step11_repositories.py` — repository and home/member isolation
  behavior.
- `tests/test_step11_5_mobile_face.py` — member face enrollment route flow.
- `tests/test_maintenance_fixes.py` — isolated repository/pairing cleanup and
  configuration safeguards.

Tests were treated as evidence only after their commands completed and pytest
reported a final result.

## Executed batches and results

### Batch 1 — desktop, stream, pairing, and DeviceSession

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m pytest -q tests\test_camera_worker_lifecycle.py tests\test_stream_integrity.py tests\test_device_pairing_client.py tests\test_device_credential_store.py tests\test_device_session_exchange.py tests\test_device_session_token.py tests\test_video_device_sessions.py tests\test_paired_home_identity.py
```

Result: **73 passed, 0 failed, 0 skipped, 2 warnings** in 17.60 seconds.

### Batch 2 — video routes, authorization, security, detection, FaceOcc

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m pytest -q tests\test_video_routes.py tests\test_security_authorization.py tests\test_face_detection.py tests\test_face_occlusion_service.py tests\test_face_occlusion_runtime.py tests\test_face_occlusion_diagnostic_publisher.py tests\test_face_occlusion_api.py tests\test_step5.py tests\test_step8.py
```

Result: **100 passed, 0 failed, 0 skipped, 4 warnings** in 56.20 seconds.

### Batch 3 — backend, repositories, members, alerts, and security logs

```powershell
$env:TEST_ISOLATED_MODE='1'
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q tests\test_backend.py tests\test_step7.py tests\test_step11_repositories.py tests\test_step11_5_mobile_face.py tests\test_maintenance_fixes.py
```

Result: **47 passed, 1 skipped, 0 failed, 5 warnings** in 11.74 seconds.

### Supplemental pairing/authentication batch

```powershell
$env:TEST_ISOLATED_MODE='1'
.\.venv\Scripts\python.exe -m pytest -q tests\test_pairing.py tests\test_device_auth.py
```

Result: **89 passed, 0 failed, 0 skipped, 2 warnings** in 31.92 seconds.

### Combined counts

- Passed: **309**
- Failed: **0**
- Skipped: **1**
- Warnings: **13**
- Timed out/incomplete batches: **0**

The batches completed sequentially. No test commands were run concurrently.

## Warnings

Observed warnings were non-failing:

1. `StarletteDeprecationWarning`: the installed Starlette test client uses
   deprecated `httpx` integration and recommends `httpx2`.
2. Supabase client deprecations for `timeout` and `verify` parameters in a
   local fallback/error-path test.
3. `InsecureKeyLengthWarning`: a test JWT HMAC key is shorter than the
   recommended 32 bytes.
4. `PytestCacheWarning`: pytest could not create
   `D:\.pytest_cache\v\cache` because an existing path caused `WinError 183`.

No warning caused a test failure. None was changed in this phase.

## Failures and incomplete tests

No executed batch failed or exceeded the diagnostic window. There were no
assertion, dependency, environment, or timeout failures to investigate.

The following broader checks were not run because they were outside the
requested desktop/backend stability batches or could involve broader behavior:

- Full repository pytest suite.
- Flutter/Dart tests or analyzer.
- Physical-camera validation.
- Live FastAPI, Supabase, or mobile integration.
- `tests/test_step5_e2e.py` and the standalone integration verifier.

Not running these is a coverage limitation, not a passing result.

## Baseline findings

- CameraWorker lifecycle coverage is now present and passing with mocked
  resources.
- FramePublisher credential/session and frame-publishing paths covered by the
  existing device/session tests are passing.
- Video authorization and stream/status route tests are passing in isolated
  mode.
- FaceOcc service, asynchronous runtime, publisher, and API tests are passing.
- Security authorization, face detection, recognition/security pipeline,
  repository isolation, member enrollment, alerts, and security-log tests are
  passing in the executed batches.
- One repository test was intentionally skipped by its existing test logic;
  it was not converted into a pass.

## Coverage gaps and risks

- No real camera, network, Supabase, or mobile runtime behavior was verified.
- Full-suite interactions and test-order effects remain unverified.
- Pytest cache-path warnings remain an environment cleanliness issue.
- Dependency deprecation warnings should be tracked separately; changing them
  would require a deliberate dependency/configuration task.
- The current evidence does not establish production latency, long-running
  worker stability, or live reconnect behavior.

## Recommended next phase

Use this passing offline baseline as the gate for a separate, explicitly
authorized controlled integration phase. The smallest next step is to review
the one skipped repository test and the non-failing deprecation warnings, then
plan a bounded live-camera/backend test without changing security decisions.

## Final safety confirmation

- No application files were modified by this phase.
- No runtime configuration or credentials were changed.
- No webcam was opened.
- No FastAPI, Flutter, Supabase, or external service was started.
- Authentication, authorization, pairing, DeviceSession, MJPEG, YuNet, SFace,
  FaceOcc, alerts, logs, and security behavior were not changed.
