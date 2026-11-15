# Installation draft

This document is a publication draft. It is intentionally limited to local development and does not authorize production deployment.

## Python desktop/backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` locally with deployment-specific values. Never commit `.env` or any credential-bearing file.

## Flutter

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
```

Use only a test backend and test account. Do not use production credentials in development builds.

## Models

Model binaries are intentionally not included in this publication draft. Obtain each model from its authoritative source, verify its checksum and license, and configure local paths without committing the files.

