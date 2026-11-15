# Phase 8.0.10 — Alternative Local PAD Model Research

**Project:** Otto Smart Home Security & Voice Assistant  
**Scope:** Offline RGB face presentation-attack detection models  
**Method:** Read-only official-source research  
**Final status:** **BLOCKED**

No model or dataset was downloaded. No package was installed, no inference or webcam was used, and no project application code was changed.

## 1. Executive summary

Several lightweight RGB PAD implementations are technically suitable for later isolated testing, but none has a complete, authoritative chain covering source code, exact trained weights, training data, private academic use, and redistribution. The recurring issue is that a permissive repository license covers source code, not automatically the checkpoint or the dataset-derived artifact.

**Conditional technical primary:** Open Model Zoo `anti-spoof-mn3`.  
**Conditional technical fallback:** Facenox MiniFASNetV2-SE.  
**Rights status for both:** unresolved; neither is approved for local artifact use or redistribution by this audit.

## 2. Comparison table

| Model | Architecture / input | Color and preprocessing | Output mapping | Runtime/deployment | Weight license | Dataset/license | Academic/private use | Public redistribution | Limitations / evidence |
|---|---|---|---|---|---|---|---|---|---|
| OMZ `anti-spoof-mn3` | MobileNetV3; 128×128 NCHW | Converted model BGR; mean `[151.2405,119.5950,107.8395]`, scale `[63.0105,56.4570,55.0035]` | `[1,2]`; 0 real, 1 spoof | ONNX/OpenVINO documented; CPU listed by OMZ; OpenCV 5 untested | Source MIT is linked; exact weight scope unresolved | CelebA-Spoof; non-commercial research and derived-data restrictions | UNCLEAR | UNCLEAR / do not bundle | Best technical contract; dataset-derived weight rights unresolved. [README](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/README.md), [metadata](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/model.yml) |
| Facenox MiniFASNetV2-SE | MiniFASNet V2 SE; 128×128 | RGB; exact normalization must be verified from inference source/artifact | Real/Spoof documented; numerical index order not independently verified | `.pth`, FP32 ONNX, INT8 ONNX; CPU demo; OpenCV 5 untested | Apache-2.0 repository; trained-weight license not explicit | README reports CelebA-Spoof; derived rights unresolved | UNCLEAR | UNCLEAR / do not bundle | Strong deployment packaging, but provenance and mapping incomplete. [README](https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/README.md), [release](https://github.com/facenox/face-antispoof-onnx/releases) |
| Yakhyo MiniFASNetV1SE/V2 | Silent-Face-derived MiniFAS variants; dimensions and exact contract require artifact inspection | Inference repository documents utilities; exact artifact preprocessing not fully verified here | README visually indicates Real/Fake/Fake, but exact per-index mapping is not established | PyTorch and ONNX Runtime utilities; OpenCV 5 untested | Apache-2.0 repository; weight rights not explicit | Dataset/provenance for published weights unresolved | UNCLEAR | UNCLEAR / do not bundle | Useful implementation reference, not a cleared artifact. [repository](https://github.com/yakhyo/face-anti-spoofing), [README](https://github.com/yakhyo/face-anti-spoofing/blob/main/README.md) |
| FeatherNet RGB | FeatherNet; approximately 0.35M parameters; CASIA-SURF CeFA RGB configuration | Exact resize, normalization, and color contract not fully documented in reviewed source | Binary classification, exact index mapping not verified | PyTorch-era code; Google Drive checkpoints; ONNX/OpenCV 5 untested | Apache-2.0 source; checkpoint license absent | CASIA-SURF CeFA terms and derived rights unresolved | UNCLEAR | UNCLEAR | Old Python/PyTorch tooling and incomplete artifact contract. [README](https://raw.githubusercontent.com/trushkin-ilya/face-anti-spoofer/master/README.md), [license](https://raw.githubusercontent.com/trushkin-ilya/face-anti-spoofer/master/LICENSE) |
| CDCN / CDCN++ | Central Difference Network; RGB and multimodal research variants | Exact production RGB preprocessing varies by configuration | Research code; exact deployable artifact mapping not verified | No stable ONNX/OpenCV 5 contract found | Research-only wording; commercial use not allowed without author contact | Dataset/checkpoint provenance and redistribution unresolved | UNCLEAR | UNCLEAR / research restrictions apply | Strong research results, weak practical artifact contract. [README](https://raw.githubusercontent.com/ZitongYu/CDCN/master/README.md), [license](https://raw.githubusercontent.com/ZitongYu/CDCN/master/LICENSE) |
| Silent-Face-Anti-Spoofing / upstream MiniFASNet | MiniFASNet family; variant-specific | Variant-specific; earlier project mapping conflict remains unresolved | Conflicting/publicly reused mappings; must verify exact checkpoint | PyTorch/mobile implementations; artifact-specific ONNX/OpenCV 5 untested | Apache-2.0 source; checkpoint rights not established | Dataset provenance varies and is not established per artifact | UNCLEAR | UNCLEAR | Cannot select a weight without a specific provenance record. [repository](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing), [license](https://raw.githubusercontent.com/minivision-ai/Silent-Face-Anti-Spoofing/master/LICENSE) |
| Research-only/custom alternatives | Papers and third-party forks | Varies | Often incomplete | Often requires PyTorch or custom export | Usually not artifact-specific | Often restricted or undocumented | UNCLEAR | UNCLEAR | Not suitable for this phase without primary artifact evidence. |

## 3. Candidate details

### 3.1 Open Model Zoo `anti-spoof-mn3`

This is the strongest technical candidate. OMZ publishes the exact ONNX filename, size, checksum, original source identifier, input shape, normalization, channel conversion, and class mapping. The model card identifies MobileNetV3 and CelebA-Spoof provenance. OMZ’s model metadata links an Apache-2.0 `training_extensions` license, while the model README links the original kprokofi MIT license.

That evidence is not enough to conclude that the trained artifact is free of CelebA-Spoof-derived restrictions. The exact file should remain outside the project until a rights holder confirms private academic use and any distribution policy. OpenCV 5 CPU loading has not been tested.

### 3.2 Facenox MiniFASNetV2-SE

Facenox is the most practical fallback from a deployment perspective. It publishes FP32 and quantized ONNX artifacts, documents CPU inference and 128×128 RGB input, and supplies an export pipeline. The README reports CelebA-Spoof evaluation and says the repository is Apache-2.0.

The remaining blockers are material: the repository license does not clearly identify a separate grant for the trained binaries, the exact numeric output order is not established by the reviewed contract, and CelebA-Spoof-derived rights remain unresolved.

### 3.3 Yakhyo MiniFAS variants

This repository is a useful implementation reference because it provides minimal PyTorch and ONNX Runtime inference utilities and publishes weight files in the repository structure. However, the Apache-2.0 repository label does not itself establish weight rights, training-data provenance, or private academic permission. It is not selected as primary or fallback.

### 3.4 FeatherNet RGB

FeatherNet is lightweight and explicitly has an RGB configuration, but its published checkpoints are external links and the repository documents older Python/PyTorch assumptions. The reviewed sources did not provide a complete inference contract or checkpoint license. It is not ready for a controlled artifact phase.

### 3.5 CDCN / CDCN++

CDCN has credible published research results and an official implementation, including RGB research results. The repository explicitly limits the work to research and disallows commercial use without author contact. No complete CPU/OpenCV 5/ONNX artifact contract was identified. It remains a research reference only.

### 3.6 Silent-Face-Anti-Spoofing / MiniFASNet family

The upstream repository is Apache-2.0 at the source level, but earlier project work identified unresolved class mapping and checkpoint provenance questions. A model-family name is not enough to establish the rights or output mapping for a particular binary.

## 4. Rights assessment

### Explicitly documented

- OMZ and the candidate repositories publish source/documentation license files.
- The OMZ model card documents an original MIT license link for the original model source.
- CelebA-Spoof explicitly states non-commercial research use and restricts further copying, publishing, or distributing the dataset and derived data.
- CDCN explicitly states research-only use and that commercial use is not allowed.

### Not explicitly documented

- A complete license covering each trained checkpoint.
- Whether “derived data” in CelebA-Spoof includes trained or converted weights.
- Permission for private university FYP execution or supervisor demonstrations.
- Permission for public weight redistribution, application bundling, or GitHub Releases.
- Artifact-specific output-index mapping for several candidates.

## 5. Academic and publication matrix

| Activity | OMZ | Facenox | FeatherNet | CDCN | Silent-FAS/Yakhyo |
|---|---|---|---|---|---|
| Local private testing | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR |
| Private webcam demonstration | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR |
| Supervisor/evaluator review | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR | UNCLEAR |
| Public Otto source code | Conditionally compatible | Conditionally compatible | Conditionally compatible | Research-only conditions | Conditionally compatible |
| Public model link | Link only; verify attribution | Link only; verify attribution | Link only; verify attribution | Link only; verify terms | Link only; verify terms |
| Bundled weights | NO-GO | NO-GO | NO-GO | NO-GO | NO-GO |
| Commercial use | NO-GO/UNCLEAR | NO-GO/UNCLEAR | UNCLEAR | Prohibited without author contact | UNCLEAR |

## 6. Conditional ranking

This is a technical/documentation ranking, not a legal approval or accuracy ranking.

1. **OMZ anti-spoof-mn3 — conditional primary:** best exact artifact metadata, preprocessing, mapping, and CPU documentation.
2. **Facenox MiniFASNetV2-SE — conditional fallback:** best published ONNX packaging and CPU-oriented workflow after OMZ.
3. **Yakhyo MiniFAS variants:** useful inference reference, but artifact rights/mapping are not sufficiently explicit.
4. **FeatherNet RGB:** lightweight, but stale tooling and weak artifact-rights/deployment documentation.
5. **CDCN/CDCN++:** credible research, not a practical rights-cleared local artifact.
6. **Upstream Silent-FAS/MiniFAS variants:** unresolved checkpoint mapping and provenance.

## 7. Required next phase for any candidate

Only after written rights clarification:

1. Create a disposable environment outside the project.
2. Obtain one exact artifact from an authoritative source.
3. Record URL, version, checksum, license, and provenance.
4. Inspect input/output names, shapes, operators, and metadata.
5. Test CPU loading through OpenCV 5 `cv2.dnn.readNetFromONNX()`.
6. Run synthetic-input smoke tests only.
7. Verify output mapping against source documentation and controlled fixtures.
8. Measure latency without webcam or application startup.
9. Keep the artifact outside the project until the rights and validation reports pass.

## 8. Recommendation

Do not implement or integrate a PAD model yet. Treat OMZ as the next conditional technical candidate and Facenox as the fallback, but treat both as **rights-blocked** until their trained-weight and dataset-derived permissions are answered in writing or by complete artifact-specific terms.

## Final status

**BLOCKED** — no researched candidate currently satisfies all required conditions for explicit weight rights, dataset provenance, academic-use permission, and public redistribution compatibility. Local offline implementation remains feasible technically, but rights clarification and isolated artifact verification must precede it.

