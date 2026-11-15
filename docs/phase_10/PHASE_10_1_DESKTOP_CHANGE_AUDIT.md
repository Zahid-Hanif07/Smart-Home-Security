# Phase 10.1 Desktop Microphone Change Audit

Status: **PASS**

## Scope and safety

This is a read-only attribution audit. No application, test, configuration,
desktop, Flutter, or documentation file was changed except for creating this
requested report. No reset, checkout, restore, clean, stash, or destructive
operation was used.

No desktop application, backend, mobile application, camera, microphone, or
physical audio device was started or accessed.

## Overall desktop impact

**LIMITED**

Phase 10.1 added a separate desktop microphone service and visible Push-to-Talk
controls to the PySide6 dashboard. It did not alter the camera-processing
implementation, but it did change the desktop dashboard surface and its
shutdown path. Under the revised requirement, those Phase 10.1 desktop audio
changes should be removed or isolated. The dashboard file also contains many
pre-existing changes from earlier FaceOcc/pairing work, so restoring the whole
file would be unsafe.

## Exact desktop files changed or added

The current worktree shows these desktop-related paths:

### Phase 10.1 desktop audio changes

- `app/ui/main_window.py` — modified; contains both earlier unrelated changes
  and Phase 10.1 microphone additions.
- `app/voice/__init__.py` — untracked, created for the desktop voice package.
- `app/voice/audio_capture.py` — untracked, desktop QtMultimedia capture service.
- `tests/test_voice_audio_capture.py` — untracked, desktop audio unit tests.

### Desktop paths modified before Phase 10.1 or not attributable to its audio
scope

The current worktree also contains earlier desktop changes in:

- `app/ui/camera_worker.py`
- `app/streaming/frame_publisher.py`
- `app/streaming/frame_manager.py`
- `app/security/security_service.py`
- `app/security/face_recognition_service.py`
- `app/services/api_client.py`
- `app/api/*`
- `app/config/*`
- other backend/security/streaming files shown by `git status --short`

Those paths are not desktop microphone changes and were not modified in this
audit.

## Exact Phase 10.1 additions in `app/ui/main_window.py`

The following changes are directly attributable to the Phase 10.1 desktop
microphone implementation:

1. Import of `AudioCaptureService` and the audio state constants.
2. Constructor injection parameter `audio_capture=None`.
3. Creation of `self.audio_capture` and `_voice_audio_path`.
4. Connections to `state_changed`, `error_changed`, and
   `recording_finished`.
5. The `PUSH TO TALK` and `CANCEL` buttons.
6. The `Voice: Ready` status label.
7. `toggle_voice_recording()`.
8. `cancel_voice_recording()`.
9. `_on_audio_state_changed()`.
10. `_on_audio_error()`.
11. `_on_audio_recording_finished()`.
12. `clear_voice_audio_artifact()`.
13. `closeEvent()` calls to cancel audio and delete the temporary artifact.

These additions are visible in the current diff around the constructor,
controls panel, and close handler. They are the only microphone-related code
found in the desktop dashboard.

## Desktop audio files inspected

### `app/voice/audio_capture.py`

This is a new independent service using the existing PySide6 QtMultimedia API:

- `QMediaDevices.defaultAudioInput()` checks the default input.
- `QAudioSource` captures 16 kHz mono 16-bit PCM into a `QBuffer`.
- `stop()` creates a temporary WAV file.
- `cancel()` and `dispose()` release Qt audio resources.
- Generic states include ready, recording, stopped, permission denied,
  microphone unavailable, and recording failed.

It is not referenced by the camera worker or security services. It is only
referenced by `MainWindow`.

### `tests/test_voice_audio_capture.py`

This new test file covers mocked/no-device behavior, duplicate start, safe stop,
recording failure cleanup, temporary-file deletion, and WAV handoff. It does
not access a physical microphone.

The test file is independent of existing YuNet, SFace, FaceOcc, camera,
pairing, security-event, MJPEG, and backend tests.

## Existing desktop code that may have been altered

The comparison against the repository baseline shows `app/ui/main_window.py`
also contains changes that are not Phase 10.1 microphone work. Examples include:

- `FaceOcc` imports, status badge, signal connection, rendering, and reset
  logic.
- `PairCameraDialog` import, Pair Camera button, and pairing handler.
- Changed initial database-status behavior.
- Changed door badge from `LOCKED` to `NOT CONNECTED`.
- Changed identity handling for `UNVERIFIED` and dynamic status text.
- Existing imports such as `time`, `QDialog`, and FaceOcc constants supporting
  those features.

These changes are visible in the same file diff but are documented by earlier
phases and cannot safely be attributed to Phase 10.1. They should not be
removed as part of desktop microphone cleanup.

The full file diff also shows earlier behavior changes such as removing the
local-database empty check from `on_identity_updated()`. That is a manual-review
item from an earlier phase, not evidence that Phase 10.1 changed security
behavior.

## Security functionality assessment

The Phase 10.1 microphone additions do not call or modify:

- `CameraWorker`
- YuNet face detection
- SFace recognition or thresholds
- `SecurityService`
- motion detection
- security-event generation
- authentication or authorization
- DeviceSession or pairing
- FramePublisher or FrameManager
- MJPEG streaming
- FaceOcc inference or diagnostic publishing
- backend routes, alerts, or security logs

The only desktop lifecycle effect is that `MainWindow.closeEvent()` now also
cancels the audio service and deletes its temporary artifact. That is isolated
from the camera worker cleanup, but it is still a desktop behavior change and
should be removed under the revised desktop requirement.

No evidence was found that Phase 10.1 removed or replaced existing camera or
security code. However, because `main_window.py` was already dirty before this
phase, attribution of every non-audio line to a particular earlier phase is
not provable from the current worktree alone.

## Changes that can safely be removed

Subject to a separate approved implementation task, the following are the
narrowly scoped Phase 10.1 desktop removals:

1. Remove `app/voice/audio_capture.py` and `app/voice/__init__.py` together,
   because they have no non-voice callers identified in the project.
2. Remove `tests/test_voice_audio_capture.py`, because it tests only the
   desktop audio service.
3. In `app/ui/main_window.py`, remove only:
   - the `app.voice.audio_capture` import block;
   - the `audio_capture` constructor parameter and related instance fields;
   - the three audio signal connections;
   - the Push-to-Talk/Cancel controls and voice status label;
   - the five audio helper methods;
   - the two audio cleanup calls in `closeEvent()`.

These removals do not require restoring the entire dashboard file and should
leave the earlier FaceOcc, pairing, camera, and security changes intact.

## Changes requiring manual review

- The exact hunk boundaries in `app/ui/main_window.py` should be reviewed before
  removal because the file has unrelated FaceOcc and pairing changes adjacent
  to the microphone additions.
- `MainWindow.__init__(audio_capture=None)` is an API extension. Search confirms
  no known production caller needs it, but tests or external local tooling may
  instantiate `MainWindow` with that optional argument.
- The Phase 10.1 report states the desktop audio tests passed, but that does
  not prove the service works with real hardware; no hardware test is needed
  for cleanup.
- The current `docs/phase_10/PHASE_10_1_MICROPHONE_PUSH_TO_TALK.md` documents
  the desktop implementation and should be retained as historical evidence or
  updated in a separate documentation decision; it is not runtime code.
- `app/ui/main_window.py` is already modified in the worktree, so any cleanup
  must use a targeted patch rather than a whole-file restore.

## Flutter changes reviewed separately

Flutter voice changes remain separate and were not removed or modified:

- `mobile/lib/features/voice/services/android_audio_recorder.dart`
- `mobile/lib/features/voice/provider/voice_provider.dart`
- `mobile/lib/features/voice/widgets/voice_control_button.dart`
- `mobile/test/voice_provider_test.dart`
- Provider/UI wiring in `mobile/lib/app/app.dart` and
  `mobile/lib/features/home/presentation/home_screen.dart`
- Android `RECORD_AUDIO` permission and MethodChannel code in
  `mobile/android/app/src/main/AndroidManifest.xml` and
  `MainActivity.kt`

Those changes are consistent with the revised mobile-only requirement and are
outside this desktop audit.

## Can the original desktop dashboard be preserved?

Yes. The original/pre-Phase-10.1 desktop behavior can be preserved without
restoring the entire `app/ui/main_window.py` file. The safe approach is a
targeted removal of only the audio import, audio state, audio controls,
audio handlers, and close-event cleanup. Earlier FaceOcc, pairing, and other
worktree changes must remain untouched unless separately approved.

## Recommended safe cleanup steps — not executed

1. Make a separate approved change limited to the files listed under “Changes
   that can safely be removed.”
2. Use a targeted patch against the audio-specific hunks in
   `app/ui/main_window.py`; do not use `git restore` or replace the file.
3. Re-run `git diff` and confirm no FaceOcc, pairing, camera, or security hunk
   was removed.
4. Run Python compilation and existing offscreen UI tests.
5. Confirm no `app.voice` import remains in desktop production code.
6. Leave all Flutter voice files unchanged.

## Final confirmation

- No cleanup was executed.
- No existing file was deleted, restored, reset, or reverted.
- No desktop application, backend, mobile application, camera, microphone, or
  audio device was started or accessed.
- Phase 10.2 was not started.

Final status: **PASS**
