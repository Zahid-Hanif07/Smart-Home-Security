# Phase 8.0.7 — PAD Licensing Clarification & GitHub Publication Preparation

**Project:** Otto Smart Home Security & Voice Assistant  
**Scope:** Read-only publication audit and documentation preparation  
**Status:** **PARTIAL**

This phase did not change runtime behavior, authentication, authorization, camera processing, model inference, MJPEG streaming, or security decisions. No model was downloaded or executed, and no message was sent to a maintainer.

## 1. CDCN correction

The CDCN row in `docs/phase_8/PHASE_8_0_6_USAGE_RIGHTS_ASSESSMENT.md` was corrected:

- Before: private local academic testing was marked `ALLOWED`.
- After: it is marked `UNCLEAR` because the reviewed sources contain research-only wording but do not document explicit permission for this exact private FYP activity.

No other Phase 8.0.6 findings were intentionally changed.

## 2. Maintainer inquiry drafts

Created separate, unsent drafts:

- `docs/phase_8/maintainer_inquiries/OMZ_anti_spoof_mn3.md`
- `docs/phase_8/maintainer_inquiries/Facenox_MiniFASNetV2_SE.md`
- `docs/phase_8/maintainer_inquiries/CelebA_Spoof_dataset.md`

They ask about private FYP use, local webcam evaluation, supervisor/evaluator demonstrations, source publication, weight redistribution, ONNX conversion, attribution, and dataset-derived restrictions. No email, issue, or form was submitted.

## 3. Publication security audit

### Configuration and credentials

- `.env` patterns are ignored by the current `.gitignore`; this is appropriate, but the final repository should also explicitly ignore common local variants and secret stores.
- `.env.example` contains placeholders rather than observed secret values. It documents sensitive variables including Supabase service-role/JWT settings, access tokens, home IDs, and model paths. It must remain placeholder-only.
- Source files contain authentication, token, device-credential, and pairing mechanisms. These are publication-sensitive implementation areas and must be reviewed for hard-coded values before release.
- No secret values were printed or included in this report.

### Models and datasets

The working tree contains or references sensitive/restricted artifacts that should not be published without an artifact-by-artifact rights review:

- `models/*.onnx`, `models/*.caffemodel`, `models/*.prototxt`, and `models/faceocc_source/`.
- `FaceOcc_Test_Images/` and any generated pseudo-mask or validation directories.
- Local FaceOcc virtual environments and caches such as `.faceocc_venv/`.
- Any `data/faces/`, `data/face_database/`, `data/security_evidence/`, logs, exports, screenshots, or database files.

The tracked model files include YuNet/SFace-related binaries and a Caffe model. Their exact redistribution notices were not established in this phase. They should be treated as publication blockers until verified or removed from the public release.

### Personal and biometric data

Do not publish:

- webcam frames, face crops, personal images, screenshots containing faces;
- SFace embeddings or face databases;
- home/device identifiers, pairing codes, access tokens, security logs, alerts, or evidence;
- generated masks, annotations, or dataset-derived files.

The existing `FaceOcc_Test_Images/` directory contains category folders and image files in the working tree. It must be excluded unless every image has documented permission and no personal-data concern.

### Existing documentation risks

- The existing root `README.md` contains an old absolute Windows path and a roadmap that does not describe the current backend/mobile/FaceOcc boundaries accurately.
- The existing README describes model files under `models/` without license provenance. It should not be treated as publication-ready.
- No completed `THIRD_PARTY_NOTICES.md`, model-rights register, or privacy policy was found before this phase.

## 4. Files and categories that must be excluded

At minimum, exclude or review before publication:

```text
.env
.env.*              # except intentionally reviewed templates
.venv/
.faceocc_venv/
data/
FaceOcc_Test_Images/
models/*.onnx
models/*.caffemodel
models/faceocc_source/
*.sqlite
*.db
*.log
*security_evidence*
*embedding*
*credential*
*token*
mobile/mobile.7z
build/
.dart_tool/
```

The exact ignore policy must be reviewed against required distributable assets so that it does not accidentally hide source files or approved test fixtures.

## 5. Proposed documentation structure

Created publication drafts under `docs/phase_8/proposed/`:

- `README.md`
- `INSTALLATION.md`
- `ARCHITECTURE.md`
- `SECURITY_AND_PRIVACY.md`
- `MODEL_LICENSES.md`
- `THIRD_PARTY_NOTICES.md`

These are proposed documents and do not overwrite the existing root README. They intentionally tell users to obtain model binaries from authoritative sources and not to commit credentials or personal data.

### Recommended future root layout

```text
README.md
.gitignore
.env.example
THIRD_PARTY_NOTICES.md
docs/
  INSTALLATION.md
  ARCHITECTURE.md
  SECURITY_AND_PRIVACY.md
  MODEL_LICENSES.md
app/
mobile/
tests/
```

Before release, the proposed documents should be reviewed against the actual current routes, startup commands, dependency versions, and supported platforms.

## 6. License and notice gaps

- No project-level license was selected or added. That decision should be made only after reviewing compatibility with bundled third-party source and model artifacts.
- The project uses multiple ecosystems: Python packages, Flutter/Dart packages, OpenCV models, Supabase libraries, and mobile platform assets. Their notices need a release-time inventory.
- YuNet, SFace, Caffe, FaceOcc, and any PAD artifact need separate source, weight, conversion, dataset, and redistribution records.
- A source-code MIT/Apache license does not automatically license pretrained weights or training-data-derived artifacts.
- CelebA-Spoof terms state non-commercial research use and restrict further copying, publishing, or distributing the dataset and derived data. The effect on each trained/converted checkpoint remains unresolved.
- CDCN is now conservatively marked `UNCLEAR` for private academic testing; its research-only wording is not treated as automatic permission.

## 7. Outstanding PAD questions

Written confirmation is still needed for:

1. Whether OMZ `anti-spoof-mn3` weight and ONNX redistribution is covered by the linked MIT/source terms.
2. Whether Facenox’s published artifacts have a separate weight license and what exact output mapping they use.
3. Whether CelebA-Spoof “derived data” includes trained checkpoints and converted ONNX files.
4. Whether FeatherNet checkpoints and CASIA-SURF CeFA provenance permit the intended academic uses.
5. Whether Silent-FAS/MiniFAS artifacts have checkpoint-specific rights distinct from the Apache-2.0 source repository.

## 8. Recommended publication sequence

1. Remove or exclude credentials, local data, personal images, logs, embeddings, generated artifacts, and unverified model binaries.
2. Verify every tracked model file’s source, checksum, license, and redistribution terms.
3. Replace the stale root README with a reviewed version based on the proposed documents.
4. Complete third-party notices and choose a project license only after the dependency/model review.
5. Run a clean-clone secret scan and inspect the complete Git diff before any commit or push.
6. Publish source/configuration and authoritative model links only; do not bundle unresolved weights.
7. Keep FaceOcc and PAD diagnostic-only in the public documentation; do not describe them as production security controls.

## 9. Exact files created or modified

Modified:

- `docs/phase_8/PHASE_8_0_6_USAGE_RIGHTS_ASSESSMENT.md` — CDCN private-testing status corrected to `UNCLEAR`.

Created:

- `docs/phase_8/PHASE_8_0_7_GITHUB_PUBLICATION_PREPARATION.md`
- `docs/phase_8/maintainer_inquiries/OMZ_anti_spoof_mn3.md`
- `docs/phase_8/maintainer_inquiries/Facenox_MiniFASNetV2_SE.md`
- `docs/phase_8/maintainer_inquiries/CelebA_Spoof_dataset.md`
- `docs/phase_8/proposed/README.md`
- `docs/phase_8/proposed/INSTALLATION.md`
- `docs/phase_8/proposed/ARCHITECTURE.md`
- `docs/phase_8/proposed/SECURITY_AND_PRIVACY.md`
- `docs/phase_8/proposed/MODEL_LICENSES.md`
- `docs/phase_8/proposed/THIRD_PARTY_NOTICES.md`

No application source, backend, Flutter code, configuration behavior, model, dataset, or environment file was modified.

## Final status

**PARTIAL** — publication documentation and unsent clarification drafts are prepared, but public release is not yet safe to claim. Credential/privacy review, model-artifact rights, third-party notices, and a final clean-clone audit remain outstanding.

