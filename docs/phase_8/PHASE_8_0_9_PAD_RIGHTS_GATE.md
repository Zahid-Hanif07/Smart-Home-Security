# Phase 8.0.9 — PAD Model Rights Gate

**Project:** Otto Smart Home Security & Voice Assistant  
**Scope:** Local offline RGB PAD candidates  
**Investigation:** Read-only licensing and usage-rights gate  
**Final status:** **BLOCKED**

No model artifact or dataset was downloaded. No package was installed, no inference or webcam was used, no maintainer was contacted, and no application/runtime code was modified.

## 1. Decision summary

| Candidate | Technical status | Private academic use | Public source publication | Public weight redistribution | Commercial use | Gate result |
|---|---|---|---|---|---|---|
| OMZ `anti-spoof-mn3` | Exact ONNX metadata and preprocessing documented; local OpenCV 5 runtime untested | **UNCLEAR** | **ALLOWED for Otto-owned code with notices**, subject to third-party review | **UNCLEAR — do not distribute** | **UNCLEAR** | **NO-GO** |
| Facenox MiniFASNetV2-SE | ONNX artifacts and CPU demo documented; exact mapping and artifact rights unresolved | **UNCLEAR** | **ALLOWED for Otto-owned code with notices**, subject to third-party review | **UNCLEAR — do not distribute** | **UNCLEAR** | **NO-GO** |

The gate is blocked because neither candidate has an authoritative, artifact-specific permission chain covering the intended trained weights and the relevant training dataset restrictions.

## 2. Official evidence reviewed

### OMZ `anti-spoof-mn3`

- [Official OMZ model README](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/README.md)
- [Official OMZ metadata](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/model.yml)
- [OMZ Apache-2.0 repository license](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/LICENSE)
- [Linked `training_extensions` Apache-2.0 license](https://raw.githubusercontent.com/kirillProkofiev/training_extensions/kp/antispoofing/LICENSE)
- [Original kprokofi MIT license](https://raw.githubusercontent.com/kprokofi/light-weight-face-anti-spoofing/master/LICENSE)
- [Original repository](https://github.com/kprokofi/light-weight-face-anti-spoofing)

The OMZ metadata identifies:

- filename `anti-spoof-mn3.onnx`;
- size `12,270,179` bytes;
- SHA256/checksum `6de4534964b723397b3e8c995cadcf43bc007cc2f9930b95ae25f76adccece5d1d4d058d0b15117b9e4a9f758424f92a`;
- original source as a Google Drive artifact;
- input `[1,3,128,128]`, NCHW;
- mean `[151.2405,119.5950,107.8395]`;
- scale `[63.0105,56.4570,55.0035]`;
- reverse-channel conversion metadata.

The README documents converted-model BGR input and output `[1,2]` probabilities with index 0 real and index 1 spoof. It identifies the model as trained on CelebA-Spoof and links the kprokofi MIT license. This is strong technical provenance, but it is not an explicit statement that the trained or converted artifact is free of dataset-derived restrictions.

### CelebA-Spoof

- [Official CelebA-Spoof page and agreement](https://mmlab.ie.cuhk.edu.hk/projects/CelebA/CelebA_Spoof.html)

The official terms state that the dataset is for non-commercial research and restrict reproducing, copying, selling, trading, reselling, commercial exploitation, and further copying, publishing, or distributing the dataset and derived data. The page does not explicitly define whether trained checkpoints or converted ONNX models are included in “derived data.” It also does not expressly grant private FYP demonstration, supervisor sharing, or public model redistribution rights.

### Facenox MiniFASNetV2-SE

- [Official repository](https://github.com/facenox/face-antispoof-onnx)
- [Repository README](https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/README.md)
- [Repository Apache-2.0 license](https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/LICENSE)
- [Published release](https://github.com/facenox/face-antispoof-onnx/releases)

The README describes 128×128 RGB input, Real/Spoof output, CPU execution, and PyTorch/ONNX/quantized ONNX artifacts. It reports CelebA-Spoof evaluation. The repository Apache-2.0 license is clear for the repository work, but the reviewed sources do not provide a separate, unambiguous license for each trained artifact or resolve the dataset-derived-weight issue. Exact numerical class-index mapping also remains unverified.

## 3. Permission separation

### Private university FYP testing

**Status: UNCLEAR for both candidates.**

The non-commercial research purpose of CelebA-Spoof is compatible in general direction with a university FYP, but it is not an explicit permission for use of a particular third-party checkpoint. The repository/source licenses do not conclusively settle the weight and dataset chain. Do not describe private use as approved until written clarification or an artifact-specific license establishes it.

### Private supervisor or evaluator demonstration

**Status: UNCLEAR for both candidates.**

No reviewed source expressly addresses a private university demonstration or private evaluator review of the trained weights. A demonstration may involve copying or sharing the artifact, which is precisely the unresolved boundary.

### Public Otto source-code publication

**Status: CONDITIONALLY ALLOWED for Otto-owned code.**

The project may prepare and publish its own integration, configuration, schemas, and preprocessing code if it contains no copied restricted artifacts, credentials, personal data, or model binaries, and if all third-party notices are retained. This does not authorize publication of model weights.

### Public model-weight redistribution

**Status: UNCLEAR / NO-GO for both candidates.**

Do not place weights in Git history, GitHub Releases, ZIP files, installers, containers, or application packages. Do not mirror the OMZ or Facenox binaries until the exact artifact rights and dataset restrictions are answered.

### Commercial use

**Status: UNCLEAR for both candidates; not planned.**

CelebA-Spoof expressly restricts commercial purposes. OMZ/Facenox repository licenses do not independently overcome that dataset restriction. CDCN’s research-only restriction remains a separate reason not to consider it for commercial use.

## 4. Candidate-wise rights matrix

| Activity | OMZ anti-spoof-mn3 | Facenox MiniFASNetV2-SE | Evidence basis |
|---|---|---|---|
| Local download and execution | UNCLEAR | UNCLEAR | Weight grant and dataset-derived scope unresolved |
| Private RGB webcam testing | UNCLEAR | UNCLEAR | No explicit artifact-specific permission |
| University FYP demonstration | UNCLEAR | UNCLEAR | No explicit demonstration permission |
| Private supervisor/evaluator review | UNCLEAR | UNCLEAR | Sharing/copying boundary not addressed |
| Private academic submission | UNCLEAR | UNCLEAR | Artifact rights and dataset terms unresolved |
| Publish Otto source code | ALLOWED conditionally | ALLOWED conditionally | Publish only project-owned code with notices |
| Publish preprocessing/configuration | ALLOWED conditionally | ALLOWED conditionally | No binary or restricted data included |
| Link to authoritative model source | UNCLEAR/confirm attribution | UNCLEAR/confirm attribution | A link is not a license grant |
| Bundle weights in GitHub | UNCLEAR / NO-GO | UNCLEAR / NO-GO | No artifact-specific redistribution permission |
| GitHub Release weights | UNCLEAR / NO-GO | UNCLEAR / NO-GO | Same unresolved weight/data chain |
| Downloadable ZIP/application weights | UNCLEAR / NO-GO | UNCLEAR / NO-GO | Same unresolved weight/data chain |
| Commercial distribution | UNCLEAR / NO-GO | UNCLEAR / NO-GO | Dataset restrictions and absent weight clearance |

“Allowed conditionally” means only the project’s own source/configuration material, not the candidate model artifact.

## 5. Exact unresolved questions

### OMZ/original anti-spoof-mn3

1. Does the MIT license linked by the OMZ README cover the original trained checkpoint, or only source code?
2. Does it cover the exact OMZ-converted `anti-spoof-mn3.onnx` file?
3. Does the linked Apache-2.0 training-extension license apply to the trained artifact, conversion code, metadata, or only source components?
4. Does CelebA-Spoof “derived data” include these trained/converted weights?
5. Is local non-commercial FYP execution permitted?
6. Is a private supervisor/evaluator demonstration permitted?
7. May the artifact be converted to another ONNX/OpenCV-compatible form?
8. May original or converted weights be redistributed publicly?
9. What attribution and notices are required?

### Facenox MiniFASNetV2-SE

1. What license covers each `.pth`, FP32 ONNX, and INT8 ONNX artifact?
2. Does Apache-2.0 cover weights, or only repository code/documentation?
3. What is the exact Real/Spoof output-index mapping per artifact?
4. What dataset and pretrained components are in the provenance chain?
5. Are local FYP testing, private demonstration, and private academic submission permitted?
6. Are ONNX conversion and public weight redistribution permitted?
7. What notices and attribution are required?

### CelebA-Spoof

1. Does “derived data” include trained checkpoints and converted ONNX models?
2. Is private local FYP use permitted?
3. Is private supervisor/evaluator sharing permitted?
4. Is inclusion in a private academic submission permitted?
5. Are public derived-weight releases prohibited or merely not addressed?
6. Are benchmark results and non-personal screenshots publishable with attribution?

## 6. Maintainer inquiry checklist for Zahid

Before artifact verification or implementation, Zahid should send the existing drafts and record written replies for every item:

- [ ] Exact artifact filename, version, source URL, and checksum.
- [ ] Rights holder for the trained weights.
- [ ] License that explicitly covers the checkpoint.
- [ ] Whether the license covers ONNX conversion and converted artifacts.
- [ ] Permission for private local university FYP testing.
- [ ] Permission for private RGB-webcam testing.
- [ ] Permission for supervisor/evaluator demonstration.
- [ ] Permission for private academic submission and results reporting.
- [ ] Permission to publish Otto source/configuration code with an authoritative download link.
- [ ] Permission to bundle weights in GitHub, Releases, ZIPs, installers, or containers.
- [ ] Commercial-use position, even though commercial distribution is not planned.
- [ ] Required copyright, attribution, citation, and third-party notices.
- [ ] Training dataset name, license, and whether trained/converted weights are “derived data.”
- [ ] Whether any pretrained backbone or third-party component adds restrictions.
- [ ] Written confirmation retained outside the public repository.

The drafts remain unsent and were sufficiently clear; no wording changes were necessary in this phase.

## 7. Final GO / NO-GO decision

### Isolated artifact verification

**NO-GO at this time.**

The next artifact-verification phase may begin only after either:

1. written rights-holder clarification answers the checklist sufficiently; or
2. a complete artifact-specific license and provenance record explicitly covers private academic use and the planned validation activity.

Once the rights gate passes, verification must remain outside the project and use no webcam initially. It should check checksum, ONNX graph contract, preprocessing, class mapping, and OpenCV 5 CPU loading before any integration.

### PAD implementation

**NO-GO.** Do not create `AntiSpoofingService`, copy a candidate model into `models/`, alter `SecurityService`, or connect PAD output to identity, access, alerts, logs, door control, backend, or Flutter.

## 8. Files reviewed and changes

Reviewed:

- `docs/phase_8/PHASE_8_0_6_USAGE_RIGHTS_ASSESSMENT.md`
- `docs/phase_8/PHASE_8_0_7_GITHUB_PUBLICATION_PREPARATION.md`
- `docs/phase_8/PHASE_8_0_8_PAD_IMPLEMENTATION_READINESS.md`
- `docs/phase_8/maintainer_inquiries/OMZ_anti_spoof_mn3.md`
- `docs/phase_8/maintainer_inquiries/Facenox_MiniFASNetV2_SE.md`
- `docs/phase_8/maintainer_inquiries/CelebA_Spoof_dataset.md`

Created:

- `docs/phase_8/PHASE_8_0_9_PAD_RIGHTS_GATE.md`

No other file was modified.

## Final status

**BLOCKED** — the exact rights needed for private artifact use and public weight redistribution remain unresolved. Source-code publication can proceed separately only after the existing credential, privacy, model-artifact, and third-party-notice audit is completed.

