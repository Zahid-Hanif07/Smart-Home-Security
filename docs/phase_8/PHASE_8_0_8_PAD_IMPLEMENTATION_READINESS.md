# Phase 8.0.8 — Final PAD Candidate Decision & Implementation Readiness Audit

**Project:** Otto Smart Home Security & Voice Assistant  
**Scope:** Local, offline RGB face presentation-attack detection readiness  
**Audit type:** Read-only  
**Status:** **PARTIAL**

No model was downloaded, loaded, executed, or integrated. No webcam, backend, Flutter application, Supabase service, or external inference API was used. No application source file was changed.

## 1. Candidate decision

### Primary: Open Model Zoo `anti-spoof-mn3`

**Decision:** best candidate for the next isolated artifact-verification phase, but **not implementation-cleared**.

Verified from the prior research record:

- MobileNetV3 binary PAD classifier.
- Official ONNX metadata: `anti-spoof-mn3.onnx`.
- Input: `[1, 3, 128, 128]`, NCHW.
- Converted-model color order: BGR.
- Mean: `[151.2405, 119.5950, 107.8395]`.
- Scale: `[63.0105, 56.4570, 55.0035]`.
- Output: `[1, 2]` probabilities; index 0 real, index 1 spoof.
- Metadata checksum: `6de4534964b723397b3e8c995cadcf43bc007cc2f9930b95ae25f76adccece5d1d4d058d0b15117b9e4a9f758424f92a`.
- Metadata size: 12,270,179 bytes.
- OMZ documentation lists CPU support.

Unresolved:

- Whether the linked MIT/source license independently covers the trained checkpoint and converted ONNX artifact.
- Whether CelebA-Spoof “derived data” restrictions apply to these weights.
- Whether private FYP execution and webcam demonstration are expressly permitted.
- OpenCV 5.0.0 loading and inference have not been tested in this phase.

### Secondary: Facenox MiniFASNetV2-SE

**Decision:** technically promising fallback, but less ready than OMZ.

The repository documents 128×128 RGB input, Real/Spoof output, CPU use, and PyTorch/ONNX/quantized ONNX artifacts. The following remain unresolved:

- Artifact-specific trained-weight license.
- Training-data and derived-weight provenance.
- Exact numerical output-index mapping for each published artifact.
- OpenCV 5.0.0 DNN loading and inference.
- Written permission for private academic use and redistribution.

### Final candidate decision

No production PAD model is selected. OMZ `anti-spoof-mn3` is the **conditional next validation candidate**, not an approved project dependency. Facenox remains a fallback pending stronger rights and mapping evidence.

## 2. Rights blockers

The Phase 8.0.6–8.0.7 reports and inquiry drafts establish these blockers:

| Question | OMZ anti-spoof-mn3 | Facenox MiniFASNetV2-SE |
|---|---|---|
| Source-code license | Documented MIT/OMZ metadata licenses | Apache-2.0 repository license documented |
| Trained-weight license | Not explicit for the artifact | Not explicit for the artifacts |
| Dataset | CelebA-Spoof | Repository reports CelebA-Spoof |
| Dataset-derived-weight permission | Unresolved | Unresolved |
| Private academic use | Confirmation required | Confirmation required |
| Public weight redistribution | Unresolved; do not do it | Unresolved; do not do it |
| Public source/configuration publication | Possible with notices and no binaries | Possible with notices and no binaries |

The CelebA-Spoof terms are non-commercial research-oriented and restrict further copying, publishing, or distributing the dataset and derived data. The audit does not interpret whether a trained checkpoint or ONNX export is “derived data”; rights-holder confirmation is required.

Written permission is not necessarily required for every local activity, but the current documentation does not establish permission clearly enough to claim clearance. Written confirmation is required before public redistribution, bundling, GitHub Releases, installers, or application ZIPs.

## 3. Artifact verification requirements

Before any implementation or project copy, perform an isolated validation outside `D:\smart_home_security`:

1. Obtain the artifact only from the authoritative source after rights review.
2. Record exact URL, filename, byte size, and SHA256.
3. Preserve the license, notices, source provenance, and download date beside the artifact.
4. Verify the OMZ checksum above.
5. Inspect the ONNX graph without running application code: input name, shape, output name, shape, and operator set.
6. Load with `cv2.dnn.readNetFromONNX()` using OpenCV 5.0.0 CPU.
7. Run only deterministic synthetic-input smoke tests initially.
8. Confirm preprocessing exactly: crop contract, resize, channel order, mean, scale, layout, and output mapping.
9. Compare repeated outputs for deterministic behavior.
10. Validate with authorized, non-personal face crops only after smoke tests pass.
11. Do not copy the artifact into the production repository until rights and validation are complete.

The prior research did not perform these steps for a PAD artifact. They must not be inferred from the FaceOcc validation history.

## 4. Local environment readiness

Inspection used imports and version queries only; no model was loaded.

| Environment | Result |
|---|---|
| System Python | 3.12.10 |
| Project `.venv` Python | 3.14.3 |
| Project `.venv` OpenCV | 5.0.0 |
| Project `.venv` NumPy | 2.5.3 |
| Project `.venv` PySide6 | 6.11.2 |
| Project `.venv` `onnx` package | Not installed |
| Project `.venv` `onnxruntime` package | Not installed |
| System Python OpenCV/ONNX/NumPy/PySide6 imports | Unavailable in the inspected interpreter |

OpenCV’s DNN module can, in principle, read ONNX without the separate `onnxruntime` package. That compatibility is **UNTESTED** for both candidates. No dependency installation is authorized in this audit.

The current project also contains model-loading code for YuNet and SFace. YuNet’s existing detector can download its model if absent; a future PAD service must not copy that behavior. PAD model loading should fail closed and report a sanitized unavailable state without downloading anything.

## 5. Existing architecture integration points

### Current verified flow

- `app/security/face_detection_service.py` — `FaceDetectionService.detect_faces()` uses YuNet and returns face dictionaries containing a bounding box, confidence, and YuNet raw landmarks.
- `app/security/face_embedding_service.py` — existing SFace model/alignment and embedding path.
- `app/security/face_recognition_service.py` — `FaceRecognitionService.recognize_face()` and `recognize_faces()` determine identity using existing embeddings and threshold `0.363`.
- `app/security/security_service.py` — `SecurityService.process_security_frame()` samples faces, calls recognition, and sends existing security-event results.
- `app/ui/camera_worker.py` — camera-thread orchestration; currently starts/stops the asynchronous diagnostic FaceOcc runtime and publisher.
- `app/security/face_occlusion_service.py` — diagnostic FaceOcc segmentation only; it is not a PAD classifier and must remain separate.
- `app/security/face_occlusion_runtime.py` — asynchronous diagnostic runtime that copies YuNet crops and landmarks.
- `app/config/settings.py` — current model-path and runtime configuration conventions.

### Safe future PAD boundary

```text
Camera frame
    ↓
YuNet face detection
    ↓
Existing SFace identity recognition (unchanged)
    ↓
Separate local AntiSpoofingService on copied YuNet face crops
    ↓
Diagnostic result first; security decision only after independent validation
```

The service should accept a BGR crop and explicit face metadata, perform local ONNX CPU inference, and return a typed result such as `real`, `spoof`, `uncertain`, `unavailable`, or `failed`. It must not receive or return embeddings, credentials, raw frames beyond the local crop, or backend state.

The first implementation should be diagnostic-only. It must not change the existing recognition result, threshold, event service, door behavior, alerts, logs, or MJPEG stream.

## 6. Exact files that would need future changes

Only after artifact rights and isolated validation are complete:

### New file

- `app/security/anti_spoofing_service.py` — standalone OpenCV DNN PAD loader, preprocessing, output mapping, sanitized result type, and missing-model handling.

### Likely configuration/test changes

- `app/config/settings.py` — PAD model path and explicit local-only configuration, following the existing FaceOcc convention.
- `tests/test_anti_spoofing_service.py` — mocked/OpenCV-independent validation of input checks, mapping, unavailable state, and no security side effects.
- A later isolated artifact/integration test directory outside production if the model remains rights-gated.

### Later integration changes, only after diagnostic validation

- `app/security/security_service.py` — submit copied face crops to a separate service without changing recognition.
- `app/ui/camera_worker.py` — if asynchronous sampling is required; never block capture or inference threads.
- `app/ui/main_window.py` — diagnostic display only, if the desktop UI is later authorized for PAD status.

Backend, Flutter, pairing, alert, security-log, door-control, and MJPEG files do not belong in the initial PAD implementation. Any later security-decision integration would require a separate approval and validation phase.

## 7. Precise next implementation phases

### Phase 8.0.9 — Rights gate

- Obtain written replies or authoritative artifact terms for OMZ and, if needed, CelebA-Spoof.
- Resolve whether private academic execution is permitted.
- Resolve whether any public weight distribution is permitted.
- Keep the candidate blocked if answers remain silent or ambiguous.

### Phase 8.1 — Isolated artifact verification

- Use a disposable environment outside the project.
- Verify checksum, graph contract, preprocessing, output mapping, and CPU OpenCV 5 inference.
- Use synthetic inputs first; do not access the webcam.
- Produce an external verification report.

### Phase 8.2 — Standalone AntiSpoofingService

- Implement only the new service and focused tests.
- Use explicit model-path configuration.
- Never download weights automatically.
- Return `unavailable` or `uncertain` safely on missing/invalid artifacts.
- Keep it diagnostic-only.

### Phase 8.3 — Controlled offline pipeline test

- Feed authorized static face crops through YuNet-shaped fixtures and the standalone service.
- Verify SFace outputs are unchanged.
- Verify no security event or door action is caused by PAD output.

### Phase 8.4 — Optional asynchronous desktop diagnostic integration

- Sample PAD work separately from camera capture.
- Bound the queue and reject stale results.
- Display status without changing identity or access decisions.

### Phase 8.5 — Separate security-policy design review

Only after model performance and rights are established should any PAD result be considered for a security policy. That would require new threat modeling, false-reject/false-accept evaluation, user safety review, and explicit approval.

## 8. Risks and limitations

- A binary RGB PAD model may perform poorly on unseen devices, lighting, camera compression, masks, screens, prints, and replay attacks.
- Published benchmark accuracy is not evidence of performance on Otto’s webcam or crop path.
- The existing SFace and YuNet model files have not been rights-audited in this phase.
- OpenCV 5 ONNX operator compatibility is untested for both candidates.
- Python 3.14.3 is newer than some historical PAD repositories’ documented environments; compatibility must be tested in an isolated environment without changing the project venv.
- FaceOcc is segmentation-based and is not a substitute for PAD. It remains diagnostic-only.
- No production threshold should be chosen from documentation or a small validation set.

## 9. Files inspected

- `docs/phase_8/PHASE_8_0_6_USAGE_RIGHTS_ASSESSMENT.md`
- `docs/phase_8/PHASE_8_0_7_GITHUB_PUBLICATION_PREPARATION.md`
- `docs/phase_8/maintainer_inquiries/*.md`
- `app/config/settings.py`
- `app/config/backend_settings.py`
- `app/security/face_occlusion_service.py`
- `app/security/face_occlusion_runtime.py`
- `app/security/face_detection_service.py`
- `app/security/face_recognition_service.py`
- `app/security/security_service.py`
- `app/ui/camera_worker.py`
- `requirements.txt`

## Final status

**PARTIAL** — the local OpenCV runtime is suitable for a future isolated compatibility test, and the existing face pipeline exposes a safe crop boundary. However, PAD artifact rights, checkpoint provenance, OpenCV compatibility, and model behavior remain unverified. No PAD implementation should begin in the production project until the rights gate and isolated artifact verification pass.

