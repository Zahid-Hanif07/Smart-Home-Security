# Security and privacy draft

## Never publish

- `.env` files, service-role keys, JWT secrets, access tokens, device credentials, pairing codes, or private keys.
- Supabase URLs are configuration values; credentials and tokens must never be committed.
- Customer profiles, home IDs, device IDs, security logs, alerts, database exports, and local evidence.
- Face images, webcam frames, face crops, embeddings, screenshots containing people, or generated masks.
- Unreviewed model binaries, datasets, checkpoints, or derived artifacts.

## Data handling

Camera frames and recognition inputs should remain local unless an explicitly authorized feature requires sanitized metadata transport. Do not transmit raw images or biometric embeddings to the backend or mobile client.

## Safety boundary

FaceOcc and any future PAD model are experimental diagnostics. They must not independently authorize, reject, unlock, lock, alert, or create security events.

## Public issue reports

Redact credentials, tokens, home/device identifiers, personal images, logs, and stack traces containing private paths before publication.

