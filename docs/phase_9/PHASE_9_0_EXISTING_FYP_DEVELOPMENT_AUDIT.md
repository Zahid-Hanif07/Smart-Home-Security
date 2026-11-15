# Phase 9.0 — Existing FYP Development Audit

**Project:** Otto Smart Home Security & Voice Assistant  
**Root:** `D:\smart_home_security`  
**Scope:** Desktop, FastAPI/Supabase, Flutter, voice-assistant readiness, and stability  
**Audit type:** Read-only  
**Final status:** **PARTIAL**

No application files, models, credentials, data, authentication behavior, or runtime configuration were changed. PAD, anti-spoofing, and active liveness were excluded as requested.

## 1. Overall project status

The project has a substantial working foundation: desktop camera/security processing, YuNet detection, SFace recognition, Supabase/FastAPI home data, device pairing, signed device sessions, MJPEG transport, alerts, security logs, Flutter home/member/face flows, and diagnostic FaceOcc transport.

It is not yet a complete, stable end-to-end product. The largest remaining gaps are:

- no implemented voice assistant or appliance-control backend;
- door and light controls are not implemented;
- mobile security-log history is not a dedicated complete view;
- camera startup currently initiates the mobile MJPEG connection from `HomeScreen` after dashboard initialization, so lifecycle and failure behavior need focused verification;
- desktop shutdown/error paths need a dedicated cleanup audit, especially publisher shutdown when the worker exits unexpectedly;
- current worktree has extensive unrelated modifications and untracked artifacts, so release readiness is not established.

## 2. Desktop application matrix

| Area | Status | Evidence and finding |
|---|---|---|
| PySide6 dashboard shell/navigation | PARTIAL | `app/ui/main_window.py` provides status panels, camera controls, pairing dialog, event log, and Qt signal wiring. Navigation is primarily dashboard/dialog based; no broader desktop navigation shell is present. |
| Camera initialization | COMPLETE | `app/ui/camera_worker.py` opens `cv2.VideoCapture` on a `QThread`, validates `isOpened()`, and emits error/status signals. `app/camera/camera_service.py` provides a separate synchronous camera abstraction. |
| Camera worker lifecycle | PARTIAL | Start/stop and thread waiting exist. The worker releases the capture and stops FaceOcc resources in `finally`; `FramePublisher.stop()` is called by `stop()`, but unexpected worker exit does not visibly stop the frame publisher in the worker’s `finally` block. |
| Camera reconnection | PARTIAL | UI permits a later manual start after stop/error. Automatic retry/reopen of a failed physical camera is not present. |
| YuNet face detection | COMPLETE in isolation | `app/security/face_detection_service.py` uses `cv2.FaceDetectorYN`, confidence filtering, bounding boxes, raw landmarks, and multi-face lists. It currently auto-downloads YuNet if its file is absent, which is unsuitable for a strict offline release process. |
| SFace recognition | PARTIAL | `FaceRecognitionService` aligns/crops through `FaceEmbeddingService`, compares 128D embeddings using SFace cosine/L2 modes, and applies the existing threshold. Remote face-record loading is integrated, but live hardware/database behavior was not tested in this audit. |
| Face registration | PARTIAL | `app/ui/registration_dialog.py` and the Flutter registration flow capture multiple samples and call face APIs. A full desktop-to-backend registration regression was not executed. |
| Motion detection | COMPLETE in code | `MotionDetectionService.process_frame()` maintains a background model, thresholds contours, annotates motion, and returns a motion result. Hardware behavior was not tested. |
| Security events | PARTIAL | `SecurityEventService` debounces motion/authorized/unknown/system events and can dispatch through `APIClient`. The design is present; external delivery and alert/log behavior were not exercised. |
| Dashboard status/error handling | PARTIAL | Camera, motion, face, identity, backend, door, FaceOcc, log, and error badges exist. Some messages are broad and there is no comprehensive desktop error/retry state model. |
| Device pairing | COMPLETE in code / NOT VERIFIED live | `PairCameraDialog`, `DevicePairingService`, credential storage, and device-session/frame publisher code exist with focused tests. No live pairing was run here. |
| MJPEG publishing | PARTIAL | `FramePublisher` sends JPEG frames through a device session and `FrameManager`; startup and failure paths exist. Long-running reconnection and shutdown behavior were not live-tested. |
| FaceOcc display | COMPLETE as diagnostic feature | `face_occlusion_runtime.py`, `CameraWorker.face_occlusion_updated`, and `MainWindow.on_face_occlusion_updated()` provide status, metrics, sequence rejection, and stale handling. It remains separate from identity/access decisions. |
| Desktop navigation beyond camera | MISSING/PARTIAL | Pairing and registration dialogs exist, but there is no evidence of a complete desktop settings, device-management, alert-history, or automation navigation surface. |

### Desktop call path

`CameraWorker.run()` captures BGR frames → `SecurityService.process_security_frame()` → motion detection → sampled YuNet detection → SFace recognition → security-event processing. FaceOcc receives copied face crops asynchronously and publishes sanitized diagnostics separately. Annotated frames return through `frame_processed` to `MainWindow`.

## 3. Backend matrix

| Area | Status | Evidence and finding |
|---|---|---|
| FastAPI application | COMPLETE in code | `app/api/main.py` registers `/api`, root `/video`, and root `/video/face-occlusion` routers plus CORS/rate-limit middleware and `/health`. |
| Health endpoint | COMPLETE | `GET /health` returns a static health response. |
| Supabase integration | PARTIAL | Repositories and `SupabaseClientManager` exist with memory fallback for isolated tests. Live configuration and production behavior were not exercised. |
| Home management | COMPLETE in code | `/api/homes`, initial-home setup, home lookup/update/delete, and owner checks exist through `HomeRepository`. |
| Member management | COMPLETE in code | Home-scoped and member-scoped CRUD routes exist. |
| Face records/enrollment APIs | COMPLETE in code / NOT VERIFIED live | Face record and registration routes exist with home/member authorization. |
| User authentication | COMPLETE in code / NOT VERIFIED live | `get_token_header()` requires Bearer tokens and `AuthService.verify_jwt_token()` validates claims. |
| Home authorization | COMPLETE in code | Home-scoped routes call `home_repository.get_home_by_id(home_id, user_id)`. |
| Device registration/management | COMPLETE in code | Device routes and repository support device records, session state, credential hashes, and revocation. |
| Pairing | COMPLETE in code / NOT VERIFIED live | Owner-authenticated code generation and unauthenticated one-time claim flow exist. The claim code is the credential for that operation; later device-session use is separate. |
| Signed DeviceSession | COMPLETE in code / NOT VERIFIED live | `get_authenticated_device_session()` validates the signed session, expected `X-Home-ID`, device state, home binding, and revocation. |
| Security logs | COMPLETE in backend code | Home-scoped create/list routes and repositories exist. The desktop event service can submit logs. |
| Alerts | COMPLETE in backend code | Home-scoped list/create/read/delete routes and repositories exist. |
| MJPEG stream | PARTIAL | `/api/video/stream` and `/video/stream` require homeowner Bearer authorization and home ownership. The stream depends on a matching current `FrameManager` publisher and recent frame. |
| Frame publishing | PARTIAL | `/api/video/frame` and `/video/frame` accept device-session-authenticated JPEG bytes with `X-Home-ID`, size checks, and frame-manager updates. External live behavior was not tested. |
| Video status | COMPLETE in code | `/api/video/status` and `/video/status` are homeowner-authorized read-only status endpoints. They expose publisher/frame/home-match reasons without opening the camera. |
| FaceOcc metadata API | COMPLETE in code / NOT VERIFIED live | Device-session-protected publish route and Bearer/home-authorized status route use typed fields, bounded latest results, older-result rejection, freshness, and in-memory retention. State is lost on backend restart. |
| Backend restart semantics | PARTIAL | FaceOcc latest-result store is explicitly in memory. Frame manager state is also process-local; restart requires publisher reconnection. Persistent security logs/alerts use repository backing when configured. |
| API documentation/contract consistency | PARTIAL | Both `/api/video/...` and root `/video/...` aliases are intentional for existing desktop/mobile callers, but the duplication should be documented and covered by route-contract tests. |

### Backend security boundary

Bearer homeowner tokens authorize home reads. Device sessions authorize desktop frame/FaceOcc publishing. The FaceOcc API accepts metadata only; it does not accept images, masks, embeddings, logits, or probability maps.

## 4. Flutter mobile matrix

| Area | Status | Evidence and finding |
|---|---|---|
| Login | COMPLETE in code / NOT VERIFIED live | Supabase sign-in, token exposure through `AuthProvider.token`, loading/error states, and session restoration exist. |
| Signup | COMPLETE in code / NOT VERIFIED live | Registration, confirmation-pending state, resend flow, and error handling exist. |
| Home selection | COMPLETE in code | `HomeProvider` loads homes, restores selected home ID, validates selection, and persists the selected ID. |
| Home creation/edit/delete | COMPLETE in code / NOT VERIFIED live | `HomeManagementScreen`, add/edit screens, and provider methods exist. |
| Dashboard | COMPLETE in code / NOT VERIFIED live | `HomeScreen` renders security status, selected home, live camera, FaceOcc panel, recent activity, alerts section integration, and navigation. |
| Live MJPEG video | PARTIAL | `CameraStreamProvider` and `MjpegStreamService` provide stream states, retry, diagnostics, and cleanup. `HomeScreen` calls `connect()` from a post-frame callback when the backend is connected, so opening the dashboard can start the stream automatically. Actual device/backend behavior was not tested here. |
| Video status diagnostic | COMPLETE as debug-only feature | `debugCheckVideoStatus()` is guarded by `kDebugMode`, calls only `GET /video/status`, and displays a restricted field set. |
| FaceOcc panel | PARTIAL/COMPLETE diagnostic path | Model, API client, provider polling, lifecycle pause/resume, home-ID response check, stale handling, and panel exist. Full Flutter test suite was not run in this audit. |
| Security logs | PARTIAL | Recent logs appear in `RecentActivity` and an alerts route exists, but a clearly dedicated complete security-log history screen/filter/export flow was not found. |
| Alerts | COMPLETE in code / NOT VERIFIED live | `AlertsProvider`, `AlertsSection`, `AlertsScreen`, read/unread updates, polling, and safe display states exist. |
| Device pairing | PARTIAL | Homeowner pairing-code generation and desktop entry flow are represented. A complete mobile device list/status/revoke management UI is not evident from the inspected routes. |
| Face enrollment | COMPLETE in code / NOT VERIFIED live | Member detail and registration screens use the device camera, capture multiple samples, and call registration APIs. |
| Household members | COMPLETE in code / NOT VERIFIED live | Member list, add/edit/detail/delete and face-registration navigation exist. |
| Door controls | MISSING | Dashboard only shows desktop “Door Lock: NOT CONNECTED”; no implemented mobile door API/control flow was found. |
| Light/appliance controls | MISSING | Settings and dashboard contain voice/control teaser text, but no backend routes, models, or working controls were found. |
| Voice assistant UI | MISSING | A settings teaser says appliance controls are coming soon; no microphone, STT, command parser, or TTS implementation exists. |
| Navigation | COMPLETE in code / NOT VERIFIED UX | Named routes cover splash, onboarding, auth, home, home management, members, profiles, settings, alerts, and face flows. |
| Application lifecycle | PARTIAL | HomeScreen pauses FaceOcc polling on lifecycle changes and stops on route transitions. Camera stream/provider lifecycle exists, but full background/foreground stream behavior was not live-tested. |
| API error/loading handling | PARTIAL | Providers use loading flags, safe generic errors, timers, and home/token checks. Some screens still depend on broad generic messages and require end-to-end verification. |

## 5. Voice assistant matrix

| Capability | Status | Finding |
|---|---|---|
| Microphone input | MISSING | No microphone/audio capture implementation was found. |
| Speech-to-text | MISSING | No STT package, local engine, or transcription service was found. |
| Command understanding | MISSING | No intent parser, command grammar, or home-automation command dispatcher was found. |
| Text-to-speech | MISSING | No TTS implementation was found. |
| Home automation commands | MISSING | No implemented light, appliance, or door-control API/UI flow was found. |
| Offline/local feasibility | NOT VERIFIED | A local command grammar plus platform-native/offline STT/TTS could be designed, but dependencies, languages, permissions, and hardware targets have not been selected. No external AI API is required by the current code because no assistant exists yet. |

## 6. System stability findings

### Strengths

- Camera processing is placed on `CameraWorker(QThread)` rather than the Qt GUI thread.
- FaceOcc runtime and diagnostic publisher use bounded/asynchronous work and do not feed identity decisions.
- Backend routes use distinct homeowner Bearer and device-session authentication schemes.
- Frame payloads have configured size checks.
- FaceOcc results are bounded, timestamped, sequence-checked, and expire as stale.
- Flutter providers cancel polling timers on lifecycle/disposal and use generation/home/token checks for FaceOcc requests.
- MJPEG and FaceOcc transport are structurally separate.

### Risks and blockers

1. `CameraWorker` owns several background services; shutdown behavior is split between `stop()` and `run()`’s `finally`, making unexpected worker termination a priority test case.
2. Mobile `HomeScreen` starts MJPEG automatically after dashboard initialization when backend health is true. This is existing behavior, but it needs controlled verification for retry, backgrounding, home switching, and no-publisher states.
3. Mobile API configuration contains platform-specific LAN defaults and a Supabase public client configuration in source. A release audit must verify that no private credential is included and that environment/build-time configuration is intentional.
4. YuNet’s detector can download a missing model automatically, conflicting with the project’s local/offline release objective. This was not changed in this audit.
5. Face records and security events may use remote API calls during desktop initialization; offline mode and startup without a resolved home need a clearer user-facing state.
6. FaceOcc backend results are in-memory and disappear on restart; Flutter should treat an empty response after restart as waiting/unavailable, not as proof that the camera is offline.
7. There are duplicate root and `/api` video aliases. They preserve current callers but require contract tests and documentation.
8. Existing worktree changes are extensive and include untracked model/test artifacts. This is a release-management risk independent of runtime correctness.

## 7. Existing test evidence

A safe offline subset was executed with `TEST_ISOLATED_MODE=1`:

```text
pytest -q tests/test_stream_integrity.py tests/test_face_occlusion_service.py tests/test_face_detection.py
22 passed, 3 warnings in 15.15s
```

Warnings were dependency deprecation warnings and a pytest cache-path warning; no test failure occurred.

A broader backend batch was started but did not produce a completed summary during the diagnostic window, so it is **not counted as passing evidence**. No Flutter test or analyzer run was performed in this audit. No live camera, backend service, Supabase connection, or mobile application was started.

Existing focused test inventory includes desktop/backend coverage for device auth, pairing, device sessions, video routes, FaceOcc API/runtime/service, stream integrity, security authorization, and UI; Flutter tests cover API client, authentication, homes, members, onboarding, camera stream provider, FaceOcc provider, and Face Analysis panel. Presence of a test file is not treated as proof of a passing suite.

## 8. Completed features that must not be rebuilt

Future work should reuse, not replace:

- `FaceDetectionService` YuNet detection and its multi-face result structure.
- `FaceEmbeddingService` and `FaceRecognitionService` SFace alignment/embedding/matching.
- `MotionDetectionService` and `StreamIntegrityService`.
- `SecurityEventService` and existing repository/API authorization patterns.
- `FramePublisher`, `FrameManager`, MJPEG stream routes, and device-session validation.
- Pairing code/device credential/device-session flow.
- `FaceOcclusionRuntime`, FaceOcc API, publisher, and Flutter FaceOcc provider/panel as diagnostic-only components.
- `AuthProvider`, `HomeProvider`, `MembersProvider`, `AlertsProvider`, `CameraStreamProvider`, and existing route/theme conventions.

## 9. Prioritized roadmap

### Priority 0 — Release and baseline control

1. Freeze a clean baseline branch/commit after reviewing all current worktree changes.
2. Run separate desktop/backend and Flutter test matrices with captured output.
3. Audit model binaries, images, embeddings, logs, `.env` files, and generated artifacts before publication.
4. Document the canonical `/api/video` versus `/video` route aliases.

### Priority 1 — Desktop/backend stability

1. Add offline unit tests for camera-worker shutdown on camera-open failure, read failure, normal stop, and unexpected processing error.
2. Verify `FramePublisher`, FaceOcc publisher, event-service worker, and camera capture all stop without leaks or duplicate threads.
3. Add bounded retry/reconnection behavior for the desktop publisher and clear dashboard states for missing pairing, backend offline, stale frames, and home mismatch.
4. Test remote face-record startup with no home, invalid home, backend unavailable, and empty enrolled database.

Likely future files: `app/ui/camera_worker.py`, `app/streaming/frame_publisher.py`, `app/security/security_service.py`, `app/services/security_event_service.py` or `app/security/security_event_service.py`, and focused tests under `tests/`.

### Priority 2 — Flutter end-to-end reliability

1. Run and stabilize Flutter analyze and the complete test suite.
2. Add lifecycle tests for automatic MJPEG start, pause/resume, home switch, logout, retry, and stream disposal.
3. Add a dedicated security-log history screen if full history is required by the FYP scope.
4. Verify alerts, FaceOcc polling, selected-home validation, and camera stream independently against mocked API contracts.
5. Replace hard-coded platform URL assumptions with a documented build-time configuration policy before public release.

Likely future files: `mobile/lib/features/home/presentation/home_screen.dart`, `mobile/lib/features/home/provider/camera_stream_provider.dart`, `mobile/lib/core/network/mjpeg_stream_service.dart`, `mobile/lib/core/config/api_config.dart`, `mobile/lib/features/home/provider/face_occlusion_provider.dart`, and focused `mobile/test/` files.

### Priority 3 — Missing product features

1. Define the FYP scope for door/light/appliance control and hardware availability.
2. Add authenticated backend models/routes only after the physical control safety model is approved.
3. Add Flutter controls with explicit unavailable/offline states and no unsafe default action.
4. Implement voice assistant as a separate local command pipeline: microphone permission → local/offline STT → fixed intent grammar → authorized home command → explicit confirmation for high-risk actions → local/native TTS.

Likely future files: new backend routes/models/repositories, new Flutter providers/screens, platform permission files, and a new local voice service. No current voice implementation should be extended by guessing.

### Priority 4 — Controlled integration and deployment

1. Test on a fixed local network with one paired desktop, one home, and one test account.
2. Verify no FaceOcc diagnostic or future PAD signal changes identity/security behavior.
3. Verify camera/MJPEG behavior under backend restart and mobile lifecycle changes.
4. Produce installation, privacy, third-party, and recovery documentation.

## 10. Recommended first implementation task

The smallest high-value next task is **Priority 1, item 1: a focused desktop camera-worker lifecycle test matrix**, using mocked `cv2.VideoCapture`, mocked publishers, and mocked security services. It does not require a webcam or backend and directly addresses the highest stability risk before adding new product features.

## 11. Files inspected

- Desktop: `app/camera/camera_service.py`, `app/security/face_detection_service.py`, `app/security/face_embedding_service.py`, `app/security/face_recognition_service.py`, `app/security/motion_detection_service.py`, `app/security/security_service.py`, `app/security/security_event_service.py`, `app/security/face_occlusion_service.py`, `app/security/face_occlusion_runtime.py`, `app/ui/camera_worker.py`, `app/ui/main_window.py`, `app/streaming/frame_publisher.py`, `app/streaming/frame_manager.py`.
- Backend: `app/api/main.py`, `app/api/dependencies.py`, `app/api/routes/*.py`, `app/models/*.py`, `app/repositories/*.py`, `app/services/*.py`, pairing/device-session modules, and video/FaceOcc routes.
- Flutter: `mobile/lib/app`, `mobile/lib/core`, `mobile/lib/features`, `mobile/lib/providers`, `mobile/lib/models`, and `mobile/test`.
- Configuration: `requirements.txt`, `mobile/pubspec.yaml`, `.env.example`, `.gitignore`.
- Tests: selected desktop/backend tests listed above and the repository test inventory.

## Final status

**PARTIAL** — the core desktop, backend, and Flutter foundations are present and an offline Python subset passes, but voice/appliance control is missing, mobile/desktop end-to-end behavior remains partly unverified, lifecycle/reconnection risks remain, and the dirty worktree prevents claiming overall completion.

