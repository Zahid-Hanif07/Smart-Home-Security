# Phase 10.1 — Microphone and Push-to-Talk Implementation

Status: **PARTIAL**

The desktop and Android capture layers were implemented without adding a
Python or Flutter package. The implementation is local-only and push-to-talk;
STT, TTS, uploads, and command execution remain out of scope.

The status is PARTIAL because the Flutter/Dart toolchain stalled without
output during verification, so mobile tests and analyzer results could not be
confirmed. No physical microphone test was performed.

## 1. Files created

- `app/voice/__init__.py`
- `app/voice/audio_capture.py`
- `tests/test_voice_audio_capture.py`
- `mobile/lib/features/voice/services/android_audio_recorder.dart`
- `mobile/lib/features/voice/provider/voice_provider.dart`
- `mobile/lib/features/voice/widgets/voice_control_button.dart`
- `mobile/test/voice_provider_test.dart`

## 2. Files modified

- `app/ui/main_window.py`
  - Adds a minimal Push-to-Talk/Stop/Cancel control and a voice status label.
  - Injects the independent `AudioCaptureService`.
  - Cancels capture and removes the temporary artifact on window close.
- `mobile/lib/app/app.dart`
  - Registers `VoiceProvider` in the existing Provider tree.
- `mobile/lib/features/home/presentation/home_screen.dart`
  - Adds the voice control widget below the existing Face Analysis panel.
  - Cancels voice capture when the screen is disposed or the app leaves the
    resumed lifecycle state.
- `mobile/android/app/src/main/AndroidManifest.xml`
  - Adds only `android.permission.RECORD_AUDIO`.
- `mobile/android/app/src/main/kotlin/com/example/mobile/MainActivity.kt`
  - Adds the `otto.voice/audio` MethodChannel and native Android
    `MediaRecorder` implementation.

No backend, camera, FaceOcc, YuNet, SFace, pairing, authentication, MJPEG,
security-event, alert, or database file was modified.

## 3. Desktop implementation

`app/voice/audio_capture.py` provides `AudioCaptureService` using the existing
PySide6 QtMultimedia installation:

- Checks `QMediaDevices.defaultAudioInput()` only after the user presses the
  button.
- Uses `QAudioSource` with 16 kHz, mono, 16-bit PCM.
- Captures into an in-memory `QBuffer`.
- Writes a temporary WAV file only when the user stops recording.
- Supports start, stop, cancel, duplicate-start prevention, and cleanup.
- Emits only generic state/error messages; it does not log audio or paths.
- Deletes artifacts through `delete_artifact()`.

The inspected environment reported PySide6 **6.11.2** and a working
`PySide6.QtMultimedia` import. No `sounddevice`, `pyaudio`, STT, or TTS
dependency was installed, so no new Python dependency was added.

Desktop UI states include:

- Voice: Ready
- Voice: Recording
- Voice: Stopped
- Voice: Permission denied
- Voice: Microphone unavailable
- Voice: Recording failed

Recording is never started during dashboard construction or application start.
The GUI thread only starts/stops the event-driven Qt audio source; no blocking
recording loop was added.

## 4. Android implementation

`MainActivity.kt` exposes a small local MethodChannel:

- `isAvailable`
- `startRecording`
- `stopRecording`
- `cancelRecording`

The native implementation:

- Checks microphone hardware availability.
- Requests `RECORD_AUDIO` at runtime.
- Uses Android `MediaRecorder` with AAC/MPEG-4 output.
- Writes only to the application cache directory.
- Returns a temporary path only to the Flutter provider for future Phase 10.2
  handoff.
- Deletes the active and last temporary artifact on cancellation, replacement,
  or activity destruction.
- Returns generic error codes/messages without exposing stack traces or audio
  data.

No background service or automatic recording was added. App destruction and
HomeScreen lifecycle changes cancel active recording.

The Flutter layer consists of:

- `VoiceRecorder` interface for test substitution.
- `AndroidAudioRecorder` MethodChannel adapter.
- `VoiceProvider` state/error lifecycle.
- `VoiceControlButton` push-to-talk UI.

The provider does not perform STT, upload audio, call FastAPI, call Supabase,
or interact with camera/MJPEG providers.

## 5. Temporary audio lifecycle and Phase 10.2 handoff

The current handoff is intentionally narrow:

- Desktop stop returns a temporary WAV path through `recording_finished`.
- Android stop returns a temporary M4A path through the MethodChannel.
- No UI displays the path.
- No audio is transmitted.
- Cancellation and shutdown delete active temporary files.
- The next recording removes the prior Android artifact.
- Desktop exposes explicit artifact deletion for the future STT consumer.

Phase 10.2 should consume the artifact through an in-process interface, then
delete it in a `finally` cleanup block. It must not persist transcripts or
send audio to external services.

## 6. Tests

### Desktop command

```powershell
$env:QT_QPA_PLATFORM='offscreen'
.\.venv\Scripts\python.exe -m py_compile app\voice\audio_capture.py app\ui\main_window.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_voice_audio_capture.py tests\test_ui.py
```

Actual result:

- Compilation: passed.
- **13 passed, 0 failed**.
- One existing pytest cache warning (`D:\.pytest_cache` / `WinError 183`).

The tests cover unavailable microphone, duplicate start prevention, safe stop,
recording failure cleanup, temporary artifact deletion, WAV handoff, and
existing dashboard UI regression behavior.

### Flutter command attempt

The following combined command was attempted after formatting the changed Dart
files:

```powershell
dart format mobile\lib\app\app.dart mobile\lib\features\home\presentation\home_screen.dart mobile\lib\features\voice\services\android_audio_recorder.dart mobile\lib\features\voice\provider\voice_provider.dart mobile\lib\features\voice\widgets\voice_control_button.dart mobile\test\voice_provider_test.dart
Push-Location mobile
flutter test test\voice_provider_test.dart
flutter analyze
Pop-Location
```

It produced no output for more than 35 seconds. A separate `dart --version`
from `mobile` also produced no output within the diagnostic window. A process
check showed no active `dart` or `flutter` process, so the command was stopped
as the agent-owned stalled command. No Flutter pass/fail result is claimed.

Flutter tests and analyzer: **NOT VERIFIED**.

## 7. Dependencies and configuration

- Python dependency added: none.
- Flutter dependency added: none.
- Android SDK, Gradle, Kotlin, and NDK versions: unchanged.
- Backend configuration and `.env`: unchanged.
- Android permission added: `RECORD_AUDIO` only.
- iOS/macOS microphone permissions: not added because this phase targets
  Windows desktop and Android.

## 8. Security and behavior preservation

- No audio upload to FastAPI, Supabase, or a third-party API.
- No transcript or audio logging.
- No authentication or authorization changes.
- No voice-based identity or access decision.
- No door control.
- No camera or physical webcam access.
- No change to YuNet, SFace, FaceOcc, motion, security events, alerts, logs,
  pairing, DeviceSession, FramePublisher, FrameManager, or MJPEG behavior.
- No automatic microphone activation.

## 9. Known limitations

- Flutter tooling must be repaired or rerun successfully before mobile PASS can
  be claimed.
- Android native compilation was not run because Flutter/Dart verification
  stalled and this phase did not authorize dependency/toolchain changes.
- The desktop audio service was not tested against a physical microphone.
- Windows microphone privacy settings may need to permit the desktop process;
  this must be configured manually by the user if required.
- Audio format/device availability can vary by Windows host.
- STT and TTS are intentionally not implemented.

## Final result

Desktop implementation and offline mocked tests are complete. Android source
implementation is present, but Flutter/native build verification is pending.
Therefore the correct phase result is **PARTIAL**, not PASS.
