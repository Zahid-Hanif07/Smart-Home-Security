# Phase 10.1 — Targeted Desktop Microphone Removal

Final status: **PASS**

## Scope

Only the Phase 10.1 Python/PySide6 microphone and Push-to-Talk implementation
was removed. Flutter voice implementation was preserved. No application,
backend, camera, security, pairing, streaming, or FaceOcc functionality was
intentionally changed by this cleanup.

No desktop app, backend, mobile app, camera, microphone, or physical audio
device was started or accessed.

## Files removed

The following files were verified before removal and matched the Phase 10.1
desktop audio implementation identified in the audit:

- `app/voice/audio_capture.py`
- `app/voice/__init__.py`
- `tests/test_voice_audio_capture.py`

They contained only the QtMultimedia audio service/package marker and its
mocked audio tests. No remaining Python production import references them.

## Targeted `main_window.py` changes removed

Only these Phase 10.1 additions were removed from
`app/ui/main_window.py`:

- `AudioCaptureService` and audio-state imports.
- `audio_capture` constructor parameter.
- Audio service instance and temporary artifact field.
- Audio signal connections.
- `PUSH TO TALK` and `CANCEL` controls.
- Voice status label.
- `toggle_voice_recording()`.
- `cancel_voice_recording()`.
- `_on_audio_state_changed()`.
- `_on_audio_error()`.
- `_on_audio_recording_finished()`.
- `clear_voice_audio_artifact()`.
- Audio cancellation and artifact cleanup in `closeEvent()`.

The constructor is again `MainWindow(self)` with no audio dependency.

## Existing functionality preserved

The following existing or earlier-phase changes remain in `main_window.py`:

- FaceOcc imports, status badge, signal wiring, diagnostic rendering, and
  freshness display.
- Pair Camera dialog and DeviceSession/pairing integration.
- Camera start/stop controls and worker lifecycle.
- Face recognition and identity status handling.
- Existing dashboard layout, styles, event log, and camera display.
- Earlier door-status and remote-face-record behavior changes.

The final diff still contains the pre-existing FaceOcc and pairing changes;
they were not removed or restored from the repository baseline.

## Preservation checks

Static search completed with no matches for these desktop audio references in
Python source/tests:

- `app.voice`
- `AudioCaptureService`
- `PUSH TO TALK`
- `btn_voice`
- `Voice:`

Flutter files were not edited by this cleanup. The existing Flutter voice
paths remain present:

- `mobile/lib/features/voice/services/android_audio_recorder.dart`
- `mobile/lib/features/voice/provider/voice_provider.dart`
- `mobile/lib/features/voice/widgets/voice_control_button.dart`
- `mobile/test/voice_provider_test.dart`
- Existing `HomeScreen`, Provider, Android MethodChannel, and
  `RECORD_AUDIO` wiring.

## Tests executed

### Python compilation

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m py_compile app\ui\main_window.py
```

Result: **passed**.

### Desktop regression tests

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m pytest -q tests\test_ui.py tests\test_camera_worker_lifecycle.py
```

Result: **12 passed, 0 failed** in 6.45 seconds.

There was one existing pytest cache warning involving
`D:\.pytest_cache` and `WinError 183`. It did not fail the tests.

### Diff check

```powershell
git diff --check -- app/ui/main_window.py
```

Result: no whitespace errors. Git emitted its existing LF/CRLF line-ending
notice for `app/ui/main_window.py`.

## Remaining risks

- Flutter tests/analyzer remain separately unverified from the earlier Phase
  10.1 toolchain stall; this cleanup did not alter Flutter files.
- The current `main_window.py` worktree diff still combines earlier changes,
  so future cleanup must remain hunk-targeted.
- No physical microphone or desktop runtime test was performed, as required.

## Final confirmation

- Desktop microphone implementation removed.
- Flutter microphone implementation preserved.
- No production desktop `app.voice` imports remain.
- No FaceOcc, pairing, camera, security, or MJPEG functionality was removed.
- No destructive repository operation was used.
- Phase 10.2 was not started.
