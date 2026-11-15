# Architecture draft

## Components

- Desktop: OpenCV camera acquisition, YuNet detection, SFace recognition, security services, FaceOcc diagnostic runtime, and PySide6 dashboard.
- Backend: FastAPI routes, authentication, home/device authorization, temporary diagnostic transport, and Supabase-backed application data.
- Mobile: Flutter authentication, home selection, MJPEG viewing, and read-only diagnostic display.

## Trust boundaries

- Desktop credentials and device sessions are local secrets.
- Backend authorization is the authority for home and device access.
- FaceOcc is diagnostic-only and must not alter SFace identity, authorization, door decisions, alerts, or security logs.
- Mobile receives sanitized metadata, not images, masks, embeddings, logits, or model files.

## Data flow

Camera frames remain local to the desktop processing path. Only explicitly permitted metadata may cross the backend boundary. See `docs/SECURITY_AND_PRIVACY.md` for publication constraints.

