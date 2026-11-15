# Phase 10.1 Flutter Voice UI Visual Review

Status: **PARTIAL**

## Scope

This was a read-only visual review. No Flutter, desktop, backend, camera, microphone, authentication, or security code was changed. No app was launched and no audio device was accessed.

## Files inspected

- `mobile/lib/features/home/presentation/home_screen.dart`
- `mobile/lib/features/home/widgets/live_camera_preview.dart`
- `mobile/lib/features/home/widgets/face_analysis_panel.dart`
- `mobile/lib/features/voice/widgets/voice_control_button.dart`
- `mobile/lib/features/voice/provider/voice_provider.dart`
- `mobile/lib/features/voice/services/android_audio_recorder.dart`
- `mobile/lib/app/app.dart`
- `mobile/lib/app/theme/app_colors.dart`

## Verified layout and behavior

`HomeScreen` places the voice card below `LiveCameraPreview` and `FaceAnalysisPanel`, and above `RecentActivity`. `VoiceProvider` is registered by the app provider tree; recording is started only by the Push-to-talk button, not automatically.

The current voice card uses the emerald/white/champagne theme. Its static copy is:

- `Voice control`
- `Push to record locally. Speech recognition comes in the next phase.`
- Idle: `Push to talk` and `Ready for a local recording.`
- Recording: `Stop recording` and `Recording locally…`, with a cancel control.
- Permission failure: `Microphone permission denied.` or the provider's safe permission message.
- Other provider failures: microphone unavailable or recording failed status text.

The preview also represents the current HomeScreen order: camera preview, Face Analysis, voice control, Recent activity, and People.

## Visual artifacts

The following are **code-based previews**, not emulator screenshots. They were reconstructed from the inspected widget labels, layout order, colors, and state strings. They contain no real user image, token, audio, or runtime data.

- [Home screen idle preview](ui_preview/home_screen_idle_preview.png)
- [Voice idle preview](ui_preview/voice_idle_preview.png)
- [Voice recording preview](ui_preview/voice_recording_preview.png)
- [Voice permission-error preview](ui_preview/voice_permission_error_preview.png)

Each PNG is 900×1700 and includes a visible `code-based preview` label.

## Runtime verification limits

No Android emulator or running Flutter window was available during inspection, so an actual full-resolution app capture and real navigation could not be performed. Recording, permission prompts, loading states, provider transitions, and lifecycle behavior were therefore not runtime-verified. The previews show the safely representable states only; they do not prove device-level microphone behavior.

## Preservation confirmation

Only the requested review document and preview PNG artifacts were created. Existing Flutter source files, tests, desktop code, backend code, configuration, camera behavior, authentication, pairing, and security behavior were not modified.

