# Phase 10.0 — Voice Assistant Architecture and Requirements Audit

Status: **PASS**

This document is an audit and plan only. No voice assistant code, existing
application code, dependencies, configuration, credentials, or tests were
modified.

## 1. Existing voice-related functionality

The current project contains only presentation placeholders:

- `mobile/lib/features/home/widgets/voice_control_teaser.dart`
  - Renders “Voice control” and “Hands-free appliance controls are coming
    soon.”
  - Has no microphone, speech, intent, or command callback.
- `mobile/lib/features/profile/presentation/settings_screen.dart`
  - Shows “Voice control” with a `SOON` tag.
- `mobile/lib/features/home/presentation/home_screen.dart`
  - Displays the existing dashboard and read-only/status actions, but no voice
    capture or command execution flow.

No microphone input, speech-to-text, text-to-speech, command parser, voice
provider, transcript store, or voice backend route was found.

The existing desktop application is a PySide6/OpenCV dashboard launched by
`app/main.py` through `app/ui/main_window.py`. Its controls are camera start,
camera stop, and camera pairing. No audio or voice subsystem was found.

## 2. Existing architecture relevant to voice

### Flutter

- `mobile/lib/app/app.dart` registers the existing Provider tree.
- `mobile/lib/app/routes/app_routes.dart` owns navigation.
- `mobile/lib/providers/auth_provider.dart` exposes the current Supabase
  homeowner session through `token` and `isAuthenticated`.
- `mobile/lib/providers/home_provider.dart` exposes `currentHome`, selected
  home loading, backend health, recent security events, and home lifecycle.
- `mobile/lib/core/network/api_client.dart` centralizes authenticated HTTP
  calls and already provides read-only methods for video status, FaceOcc status,
  homes, members, faces, alerts, and security logs.
- `mobile/lib/features/home/provider/camera_stream_provider.dart` owns MJPEG
  connection state. Voice must not call or control this provider.

`HomeScreen` currently initializes dashboard data and, when the backend is
available, connects the MJPEG stream. A voice feature must be independent of
that lifecycle and must never call `connect()`, `retry()`, or stream cleanup
methods.

### Backend

FastAPI is registered in `app/api/main.py` and `app/api/routes/__init__.py`.
Existing authentication boundaries are:

- `app/api/dependencies.py:get_current_user` and
  `get_current_user_id` validate homeowner Bearer JWTs.
- `get_authenticated_device` validates the opaque `DeviceToken` pairing
  credential.
- `get_authenticated_device_session` validates the signed short-lived
  `DeviceSession` bound to `X-Home-ID`.
- Home ownership is enforced by repositories such as
  `app/repositories/home_repository.py` and the home-scoped route handlers.

Relevant existing routes include:

- `GET /api/homes/{home_id}/security-logs`
- `GET /api/homes/{home_id}/alerts`
- `GET /video/status`
- `GET /api/video/status`
- `GET /video/stream` and `GET /api/video/stream`

There are no backend routes for lights, appliances, voice transcripts, speech
recognition, text-to-speech, or general command execution. No door unlock route
was found and door unlocking is intentionally excluded from the initial voice
scope.

### Desktop

- `app/ui/camera_worker.py` owns the QThread camera loop.
- `app/security/security_service.py` owns the motion, YuNet, SFace, and event
  processing path.
- `app/streaming/frame_publisher.py` and
  `app/streaming/frame_manager.py` own desktop-to-backend video transport.
- `app/services/api_client.py` handles desktop backend reporting.

Voice must be a separate service/thread. It must not run in the camera worker,
FaceOcc worker, Qt GUI callback, FramePublisher, or MJPEG path.

## 3. Current dependencies and permissions

### Python desktop environment

`requirements.txt` declares OpenCV, PySide6, FastAPI, Supabase, HTTPX,
PyJWT, pytest, keyring, and related application dependencies. It declares no
audio, STT, or TTS package.

Read-only module availability inspection found no installed modules for:

- `sounddevice`
- `pyaudio`
- `speech_recognition`
- `vosk`
- `faster_whisper`
- `whisper`
- `pyttsx3`
- `edge_tts`
- `soundfile`

Only the existing numerical/vision stack was available; this does not prove
that operating-system audio APIs are unavailable.

### Flutter

`mobile/pubspec.yaml` declares Flutter, Provider, HTTP, camera,
Supabase Flutter, and shared preferences. No speech, audio recording,
permission, or TTS package is declared.

`mobile/android/app/src/main/AndroidManifest.xml` declares Internet and Camera
permissions, but not `RECORD_AUDIO`. No microphone or speech usage description
was found in the inspected iOS/macOS permission files.

No permission changes should be made until the audio implementation is
approved.

## 4. Proposed modular voice pipeline

```text
Push-to-Talk UI
    ↓
Permission gate and bounded audio capture
    ↓
Local Speech-to-Text adapter
    ↓
Normalized transcript (memory only)
    ↓
Fixed intent grammar/parser
    ↓
Authenticated user + selected-home authorization
    ↓
Command validator and risk policy
    ↓
Existing read-only API or separately approved command API
    ↓
Safe result message
    ↓
Optional local Text-to-Speech adapter
```

Recommended boundaries:

- `VoiceController` owns push-to-talk state and cancellation.
- `AudioCapture` owns microphone permission, bounded capture, and release.
- `SpeechRecognizer` is an interface with a local implementation selected per
  platform.
- `IntentParser` accepts only a fixed grammar and returns a typed intent.
- `VoiceAuthorization` checks the existing authenticated user and selected home;
  it never treats the voice or speaker as proof of identity.
- `CommandExecutor` allows only explicitly enabled commands.
- `SpeechResponder` renders text and optionally uses local TTS.

Each adapter should have a fake implementation for offline tests. No audio
bytes, raw transcript, JWT, home UUID, or exception body should be written to
logs by default.

## 5. Initial command set

| User intent | Current backend support | Initial treatment |
|---|---|---|
| “Turn the light on” | No light/device-control route or capability model found | Planned/mock-only; reject as unavailable until a real authorized device contract exists |
| “Turn the light off” | No light/device-control route or capability model found | Planned/mock-only; reject as unavailable until a real authorized device contract exists |
| “Check security status” | Existing recent security-log and alert routes | Safe read-only command; call only the selected home’s authorized read endpoint |
| “Is camera monitoring active?” | Existing `GET /video/status` and mobile `ApiClient.getVideoStatus()` | Safe read-only command; report a small allowlisted status summary |
| “Read recent security alerts” | Existing home-scoped alerts route and `AlertsProvider` | Safe read-only command; read only the selected authorized home |
| Door unlock/lock | No approved control route found; high impact | Explicitly out of scope; never parse or execute in the first voice version |

Unknown, ambiguous, unsupported, or multi-command utterances should receive a
safe “I could not match a supported command” response and no backend request.

## 6. Authorization and privacy design

1. Require `AuthProvider.isAuthenticated` and a current non-expired
   `AuthProvider.token`.
2. Require `HomeProvider.currentHome?.id` and reject if no home is selected.
3. Pass the existing Bearer token through `ApiClient`; do not create a second
   authentication system or store a voice-specific token.
4. The backend must enforce the same home authorization as the existing routes;
   the client must not rely on a home ID supplied by speech text.
5. Re-check the selected home immediately before execution and ignore results
   from an earlier home or token generation.
6. Never use FaceOcc, SFace identity, voice characteristics, or speech content
   as a substitute for the homeowner JWT.
7. Keep microphone capture in memory, stop it when push-to-talk ends, and avoid
   recording or persistent audio storage in the initial design.
8. Do not send audio to cloud STT/TTS or external AI services.
9. Do not log transcripts by default. If debug diagnostics are temporarily
   needed, use redacted event names and remove them before release.
10. Use an allowlist for response fields. Do not speak or display tokens, home
    IDs, credentials, embeddings, images, masks, logits, or exception bodies.
11. Require explicit confirmation and a separate safety design for any future
    action with physical, financial, privacy, or security impact.

## 7. Local/offline technology options

These are candidates for later isolated evaluation only; none is installed or
approved by this audit.

### Windows desktop

| Function | Candidate | Strength | Limitation |
|---|---|---|---|
| Audio capture | Windows native audio API through a small adapter | Avoids a broad cross-platform dependency | Requires Windows-specific implementation and permission/error handling |
| Audio capture | `sounddevice` or `PyAudio` | Familiar Python APIs and easy fake boundary | New dependency; device enumeration and native backend issues must be tested |
| Offline STT | Vosk with a locally installed model | Lightweight streaming-oriented design | Requires a separately approved model download and model licensing review |
| Offline STT | `faster-whisper` | Stronger general transcription potential | Larger runtime/model footprint; CPU latency and model licensing must be evaluated |
| OS STT | Windows Speech/WinRT APIs | May avoid bundling a model | Offline availability and language support are OS-dependent and must be verified |
| Local TTS | Windows SAPI/WinRT | Native and offline-capable | Windows-specific voice availability and pronunciation behavior |
| Local TTS | `pyttsx3` | Simple Python adapter over local speech engines | Not installed; engine behavior varies by host |

The first desktop prototype should use a fake recognizer/responder in tests and
only then evaluate one local audio/STT/TTS stack in a disposable environment.

### Android Flutter

| Function | Candidate | Strength | Limitation |
|---|---|---|---|
| Speech input | Platform speech-recognition plugin such as `speech_to_text` | Small Flutter integration and push-to-talk UI | Offline behavior is platform/device dependent; may use system services |
| Raw audio | Platform recording plugin such as `record` | Explicit capture control if local STT is bundled | Adds permission and codec/platform complexity |
| Offline STT | Native Android on-device recognition or bundled engine | Keeps audio local when supported | Device/language availability must be verified; no current project support |
| Local TTS | `flutter_tts` using Android TTS | Common local response path | Voice availability and offline voice packs vary by device |

For the privacy requirement, an explicitly local engine is preferred. A system
recognition plugin must not be described as offline until device-level behavior
is verified. No Flutter package should be added until the chosen platform and
offline contract are approved.

## 8. Error handling contract

| Failure | User-facing behavior | Backend/security behavior |
|---|---|---|
| Microphone permission denied | Explain permission is needed; provide no command execution | No audio or request sent |
| No speech detected | “I did not hear a command.” | No request sent |
| STT failure/timeout | Generic retry message | No credentials or exception details exposed |
| Unknown command | “That command is not supported.” | No request sent |
| No authenticated user | Ask the user to sign in | No request sent |
| No selected home | Ask the user to select a home | No request sent |
| Backend unavailable | “OTTO cannot reach the home service.” | No retry storm; existing API timeout/error handling applies |
| Device unavailable | Report unavailable status only | Do not start camera, session renewal, or MJPEG from voice |
| Command unavailable | State that the capability is not connected | No fabricated success |
| Command execution failure | Generic failure and optional retry | Preserve existing auth/security behavior |

## 9. Future implementation roadmap

### Phase 10.1 — Push-to-Talk and audio capture

Expected future files:

- `mobile/lib/features/voice/presentation/voice_control_button.dart`
- `mobile/lib/features/voice/provider/voice_provider.dart`
- `mobile/lib/features/voice/services/audio_capture.dart`
- Platform permission files only if the selected implementation requires them.

Possible dependency: one approved platform audio/permission package. Do not
add it in this phase.

Tests:

- Permission granted/denied.
- Start/stop is bounded and idempotent.
- No audio is persisted.
- Cancellation on screen disposal.

Acceptance: push-to-talk changes state correctly, releases the microphone, and
does not affect MJPEG or existing providers.

### Phase 10.2 — Speech-to-Text

Expected future files:

- `mobile/lib/features/voice/services/speech_recognizer.dart`
- A platform/local adapter and fake recognizer.

Possible dependency: selected local/platform STT package or native bridge;
model download and license review required for bundled engines.

Tests:

- Transcript success, silence, timeout, cancellation, unsupported locale, and
  recognizer failure.

Acceptance: a transcript exists only in memory and no cloud/external request is
made.

### Phase 10.3 — Intent recognition

Expected future files:

- `mobile/lib/features/voice/domain/voice_intent.dart`
- `mobile/lib/features/voice/services/intent_parser.dart`
- `mobile/test/voice_intent_parser_test.dart`

No ML dependency is needed initially. Use normalized text and a strict fixed
grammar with explicit ambiguity rejection.

Tests:

- Exact supported phrases, common harmless variants, unknown phrases,
  ambiguous phrases, injection-like text, and high-risk phrases.

Acceptance: unsupported text never becomes a command and parser output contains
no credentials or private identifiers.

### Phase 10.4 — Authorized command execution

Expected future files:

- `mobile/lib/features/voice/services/voice_authorization.dart`
- `mobile/lib/features/voice/services/voice_command_executor.dart`
- Small additions to `mobile/lib/core/network/api_client.dart` only for
  already-supported read-only operations, if needed.
- Backend files only if a separately approved, real device-command contract is
  established.

Tests:

- Missing token, expired token, missing home, home switch during request,
  cross-home rejection, backend errors, and allowlisted response mapping.

Acceptance: read-only status commands use the existing auth/home boundaries;
lights remain rejected until actual hardware/API support exists; no door action
is possible.

### Phase 10.5 — Text-to-Speech

Expected future files:

- `mobile/lib/features/voice/services/speech_responder.dart`
- Optional platform adapter and fake responder.

Tests:

- Safe response text, cancellation, unavailable voice engine, and no sensitive
  field leakage.

Acceptance: only short allowlisted responses are spoken locally, with no token,
home ID, raw exception, or private event data.

### Phase 10.6 — Flutter integration

Expected future files:

- `mobile/lib/features/home/presentation/home_screen.dart` or a dedicated voice
  surface, only where the approved UI belongs.
- `mobile/lib/features/profile/presentation/settings_screen.dart` if the
  existing placeholder becomes a real entry point.
- Focused voice widget/provider tests.

Tests:

- Provider wiring, loading/error states, selected-home changes, lifecycle
  disposal, MJPEG independence, and existing dashboard regression tests.

Acceptance: the voice UI is push-to-talk, does not auto-listen, does not start
or stop camera streaming, and remains safe when the app is backgrounded.

### Phase 10.7 — Controlled end-to-end testing

Test only after the preceding phases pass:

- Fake audio/STT parser tests.
- Offline backend route tests with isolated storage.
- Controlled local device-status reads.
- Manual microphone permission and cancellation tests.
- Selected-home and expired-session tests.
- Explicit confirmation that MJPEG, FaceOcc, YuNet, SFace, alerts, logs, and
  door behavior are unchanged.

No physical door action, alert dispatch, external STT/TTS, or webcam test is
required for the initial read-only command set.

## 10. Features that must not be rebuilt

- Supabase homeowner authentication and JWT lifecycle.
- `HomeProvider` selected-home handling.
- `ApiClient` HTTP/error conventions.
- Existing video status and MJPEG stream services.
- Device pairing and signed DeviceSession logic.
- YuNet, SFace, FaceOcc, motion, security events, alerts, and logs.

Voice should consume these boundaries, not duplicate or bypass them.

## 11. Audit conclusion

The project has a voice-control visual placeholder but no functional voice
assistant. The safest first implementation is a mobile push-to-talk flow with
strict fixed intents and read-only status commands, backed by the existing
Supabase JWT, selected home, and `ApiClient`. Light controls are blocked until
real hardware capability and an authorized backend contract exist. Door control
must remain out of scope.

No implementation should begin until the local STT/TTS choice, permission
policy, and command authorization contract are approved.

## 12. Files inspected

- `mobile/lib/app/app.dart`
- `mobile/lib/app/routes/app_routes.dart`
- `mobile/lib/providers/auth_provider.dart`
- `mobile/lib/providers/home_provider.dart`
- `mobile/lib/core/network/api_client.dart`
- `mobile/lib/core/config/api_config.dart`
- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/home/provider/camera_stream_provider.dart`
- `mobile/lib/features/home/provider/face_occlusion_provider.dart`
- `mobile/lib/features/home/widgets/voice_control_teaser.dart`
- `mobile/lib/features/profile/presentation/settings_screen.dart`
- `mobile/pubspec.yaml`
- `mobile/android/app/src/main/AndroidManifest.xml`
- `mobile/ios/Runner/Info.plist`
- `mobile/macos/Runner/Info.plist`
- `app/main.py`
- `app/ui/main_window.py`
- `app/ui/camera_worker.py`
- `app/camera/camera_service.py`
- `app/security/security_service.py`
- `app/api/main.py`
- `app/api/dependencies.py`
- `app/api/routes/__init__.py`
- `app/api/routes/video.py`
- `app/api/routes/face_occlusion.py`
- `app/api/routes/alerts.py`
- `app/api/routes/security_logs.py`
- `app/api/routes/devices.py`
- `app/api/routes/pairing.py`
- `app/database/supabase_client.py`
- `app/repositories/home_repository.py`
- `requirements.txt`

## Final confirmation

Only this architecture document was created. No existing project file,
dependency, permission, credential, model, database, camera, backend, or
mobile behavior was changed.
