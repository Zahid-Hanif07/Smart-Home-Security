# Phase 8.0.6 — Academic and Public GitHub Usage Rights Assessment

**Project:** Otto — Smart Home Security & Voice Assistant  
**Scope:** RGB face presentation-attack detection candidates  
**Investigation type:** Read-only documentation and license review  
**Status:** **PARTIAL**

> This is a documentation assessment, not legal advice. “Allowed” below means that the cited public terms support the specific activity at the repository/license level; it does not resolve rights in third-party training data or unlabeled checkpoints.

## 1. Executive summary

No candidate is fully cleared for bundled model-weight redistribution. The strongest documented technical candidate is Open Model Zoo `anti-spoof-mn3`: its official model card specifies a MobileNetV3 binary classifier, exact preprocessing, class order, an ONNX artifact, and CPU support in OMZ documentation. Its model card links the original source MIT license. However, it is trained on CelebA-Spoof, whose official terms restrict the dataset and derived data to non-commercial research and prohibit further copying, publishing, or distribution. Those terms do not expressly answer whether the published trained checkpoint or a converted ONNX derivative may be redistributed.

Facenox MiniFASNetV2-SE is technically attractive because the repository publishes ONNX artifacts and a two-class contract, but the exact weight grant and class-index mapping still need confirmation. FeatherNet and CDCN have useful research documentation, but their checkpoints, dataset rights, and/or deployment contracts are incomplete for this project. Silent-Face-Anti-Spoofing has Apache-2.0 source metadata, but the public materials reviewed do not establish that the included weights and their training data are redistributable under Apache-2.0.

**Recommendation:** keep all candidates out of the public repository as binary weights. If a candidate is used for private evaluation, obtain and retain written rights-holder clarification for the checkpoint and its dataset provenance first. Publish only the Otto integration code, configuration schema, preprocessing description, attribution, and instructions that direct users to the authoritative source; do not mirror or bundle weights until rights are confirmed.

## 2. Evidence reviewed

Primary sources reviewed:

- [Open Model Zoo repository](https://github.com/openvinotoolkit/open_model_zoo) and [Apache-2.0 license](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/LICENSE).
- OMZ [`anti-spoof-mn3` README](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/README.md) and [model metadata](https://raw.githubusercontent.com/openvinotoolkit/open_model_zoo/master/models/public/anti-spoof-mn3/model.yml).
- Original [kprokofi anti-spoof repository](https://github.com/kprokofi/light-weight-face-anti-spoofing), [MIT license](https://raw.githubusercontent.com/kprokofi/light-weight-face-anti-spoofing/master/LICENSE), and [weight-rights issue #43](https://github.com/kprokofi/light-weight-face-anti-spoofing/issues/43).
- [CelebA-Spoof official terms](https://mmlab.ie.cuhk.edu.hk/projects/CelebA/CelebA_Spoof.html).
- [Facenox ONNX repository](https://github.com/facenox/face-antispoof-onnx), [README](https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/README.md), [Apache-2.0 license](https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/LICENSE), and [release page](https://github.com/facenox/face-antispoof-onnx/releases).
- [FeatherNet/face-anti-spoofer repository](https://github.com/trushkin-ilya/face-anti-spoofer), [README](https://raw.githubusercontent.com/trushkin-ilya/face-anti-spoofer/master/README.md), and [Apache-2.0 license](https://raw.githubusercontent.com/trushkin-ilya/face-anti-spoofer/master/LICENSE).
- [CDCN repository](https://github.com/ZitongYu/CDCN), [README](https://raw.githubusercontent.com/ZitongYu/CDCN/master/README.md), and [license](https://raw.githubusercontent.com/ZitongYu/CDCN/master/LICENSE).
- [Silent-Face-Anti-Spoofing repository](https://github.com/minivision-ai/Silent-Face-Anti-Spoofing) and [Apache-2.0 license](https://raw.githubusercontent.com/minivision-ai/Silent-Face-Anti-Spoofing/master/LICENSE).

No model artifacts, datasets, packages, webcam, backend, or mobile app were accessed or executed. No external contact was made.

## 3. Candidate assessments

### 3.1 Open Model Zoo `anti-spoof-mn3`

**Technical evidence:** The official card identifies a MobileNetV3 classifier with 3.02M parameters and 0.15 GFLOPs. The converted model takes `[1,3,128,128]` NCHW input and expects BGR. The card specifies mean `[151.2405,119.5950,107.8395]`, scale `[63.0105,56.4570,55.0035]`, and output `[1,2]` probabilities: index 0 real, index 1 spoof. The official OMZ device-support documentation lists CPU support. These are documentation findings only; OpenCV 5 loading was not tested in this phase.

**Rights evidence:** OMZ metadata links the artifact to a Google Drive original source and links an Apache-2.0 `training_extensions` license. The model README separately says the original model is distributed under the MIT license and links the `kprokofi` MIT file. The original MIT text grants broad software rights, subject to retaining notices. Neither the README nor metadata expressly states that the CelebA-Spoof-derived checkpoint/ONNX artifact is independently cleared for redistribution. The original repository issue discussing pretrained-weight use is not a formal permission grant.

**Assessment:** Best documented candidate for a later isolated artifact-verification phase, but not cleared for public weight bundling or redistribution. Private academic use is **UNCLEAR** pending checkpoint/dataset confirmation; source-code publication is supported with notices; weight distribution remains **UNCLEAR**.

### 3.2 Facenox MiniFASNetV2-SE

**Technical evidence:** The repository documents MiniFASNet V2 SE, 128×128 RGB input, two classes Real/Spoof, CPU demonstration, and published `.pth`, FP32 ONNX, and INT8 ONNX artifacts. It reports evaluation claims on CelebA-Spoof. The README and architecture document are useful deployment evidence, but the exact numerical output-index mapping was not independently established from a formal model contract in this audit.

**Rights evidence:** The repository is Apache-2.0, but the reviewed materials do not separately identify a weight copyright grant, dataset license, or permission to redistribute the trained artifacts. The CelebA-Spoof terms remain the relevant unresolved provenance issue where that dataset is used.

**Assessment:** Technically promising for isolated validation. Weight redistribution, derived-weight rights, and exact mapping are **UNCLEAR**. Do not bundle or mirror the artifacts.

### 3.3 FeatherNet RGB

**Technical evidence:** The repository documents FeatherNet at approximately 0.35M parameters and 79.99 MFLOPs, with an RGB-only CASIA-SURF CeFA configuration and linked Google Drive checkpoints. The repository is old and documents PyTorch 1.4/Python 3.7-era tooling. Exact inference preprocessing, output-index semantics, ONNX export, and OpenCV 5 compatibility were not established from the reviewed sources.

**Rights evidence:** The source repository has Apache-2.0 code metadata, but the linked checkpoint terms are not stated. The CASIA-SURF CeFA dataset terms and their effect on derived weights were not established here.

**Assessment:** **UNCLEAR** for private academic use and all weight distribution. Lower priority than OMZ and Facenox because the artifact and rights chain is less reproducible.

### 3.4 CDCN / CDCN++

**Technical evidence:** The official repository and CVPR materials document Central Difference Networks and RGB competition results, including a second-place single-modal RGB result. The README explicitly says the repository is for research and commercial use is not allowed. No stable, documented ONNX artifact or complete CPU/OpenCV 5 deployment contract was established in this audit.

**Rights evidence:** The repository license begins with a research-purpose restriction and says commercial use requires contacting the authors. The source code may be usable for the stated non-commercial academic context subject to its conditions, but checkpoint licensing, dataset terms, and redistribution permissions remain unverified.

**Assessment:** Suitable only as a research reference until rights and artifact provenance are clarified. Not a practical current deployment candidate.

### 3.5 Silent-Face-Anti-Spoofing / MiniFASNet variants

**Technical evidence:** The official repository is marked Apache-2.0 and is the upstream family for commonly reused MiniFASNet variants. Earlier project investigation found a class-mapping conflict between inference code and a model-card-style description; that mapping was not resolved by this rights audit. Exact artifact-specific preprocessing and output mapping therefore remain checkpoint-dependent.

**Rights evidence:** Apache-2.0 source licensing is documented, but the public source license does not by itself prove that every pretrained checkpoint is Apache-2.0 or that its training data permits derived-weight redistribution. The underlying dataset provenance must be checked per artifact.

**Assessment:** **UNCLEAR** for private use and weight distribution. Do not select until a specific checkpoint, mapping, provenance record, and rights notice are verified together.

## 4. Decision matrix

Legend: **ALLOWED** = supported by the cited public terms for that component; **UNCLEAR** = no direct permission or a third-party restriction remains; **PROHIBITED** = the cited terms expressly prohibit the activity.

| Candidate | Private local academic testing | University FYP demonstration | Private supervisor evaluation | Public source-code publication | Public model download link | Bundle weights in GitHub | GitHub Releases weight distribution |
|---|---|---|---|---|---|---|---|
| OMZ anti-spoof-mn3 | UNCLEAR | UNCLEAR | UNCLEAR | ALLOWED with notices | UNCLEAR; link only, do not mirror | UNCLEAR | UNCLEAR |
| Facenox MiniFASNetV2-SE | UNCLEAR | UNCLEAR | UNCLEAR | ALLOWED for repository code, subject to Apache notice | UNCLEAR; link only, do not mirror | UNCLEAR | UNCLEAR |
| FeatherNet RGB | UNCLEAR | UNCLEAR | UNCLEAR | ALLOWED for repository code, subject to Apache notice | UNCLEAR | UNCLEAR | UNCLEAR |
| CDCN/CDCN++ | UNCLEAR; research-only wording exists, but explicit permission for this exact private FYP activity was not documented | UNCLEAR; confirmation is prudent | UNCLEAR | ALLOWED for non-commercial research code with notices | UNCLEAR | UNCLEAR | UNCLEAR |
| Silent-FAS / MiniFAS variants | UNCLEAR | UNCLEAR | UNCLEAR | ALLOWED for Apache-licensed source with notices | UNCLEAR | UNCLEAR | UNCLEAR |

The conservative entries are intentional. The dataset agreement for CelebA-Spoof says it is for non-commercial research and prohibits further copying, publishing, or distributing the dataset and derived data. It does not expressly grant permission for a public GitHub release of trained weights. Therefore a permissive code license cannot be treated as a complete weight license.

## 5. Private academic use versus public GitHub publication

### Category A — private academic use

- **Local model download and execution:** technically feasible for OMZ and Facenox, but the artifact-specific weight grant is not explicit. Treat as **UNCLEAR** until the rights holder or a complete license notice confirms it.
- **Private RGB webcam testing:** no candidate terms reviewed expressly prohibit a non-commercial local test, but silence is not documented permission. Treat as **UNCLEAR** pending confirmation.
- **University demonstration, supervisor/evaluator review, and private academic submission:** these are not expressly addressed by the reviewed model-weight notices. The dataset says non-commercial research, which is compatible in purpose but does not settle artifact redistribution or presentation rights. Treat as **UNCLEAR**.
- **Screenshots and performance measurements:** publish only measurements that do not contain personal data or restricted model files. Model-result reporting is not expressly addressed by the reviewed weight terms; retain dataset/model attribution and seek confirmation if the report is public.

### Category B — public GitHub publication

- **Otto integration/source code:** generally publishable under Otto’s own license decision, while preserving third-party notices and avoiding copied restricted code. Candidate repository licenses support publication of their code components where their conditions are met.
- **Configuration and preprocessing code:** generally publishable if it contains no credentials, private paths, or copied restricted artifacts. Do not embed model binaries.
- **Instructions and authoritative links:** safest publication strategy, but do not rehost files, bypass access controls, or imply endorsement. A link is not a license grant for the linked artifact.
- **Bundled weights, GitHub Releases, downloadable ZIPs, modified/converted ONNX:** **UNCLEAR** for every candidate reviewed, and especially unresolved for CelebA-Spoof-derived models. Do not distribute until the exact checkpoint rights are documented.
- **Benchmark results and screenshots:** potentially publishable as original project output, subject to privacy, attribution, and any artifact/dataset terms. Avoid including model binaries, dataset images, or personal webcam imagery.

## 6. Source code versus trained weights

These are separate components:

| Component | Evidence | Finding |
|---|---|---|
| OMZ source/tools/metadata | OMZ Apache-2.0 repository and model metadata | Code/metadata licensing is documented; it does not automatically settle the original model artifact. |
| Original anti-spoof-mn3 source | kprokofi MIT license | Broad source-code permissions with notice retention; weight scope is not explicit. |
| OMZ converted ONNX | OMZ metadata, original-source link, model README | Artifact exists and is documented, but the rights chain is not a standalone weight license. |
| Facenox source and ONNX | Facenox Apache-2.0 repo/README/release | Repository license is clear; specific trained-weight and dataset-derived rights remain unresolved. |
| FeatherNet source/checkpoints | Apache-2.0 repository plus external checkpoint links | Code license is visible; checkpoint license is not established. |
| CDCN source/checkpoints | Research-use license and repository | Non-commercial research restriction is explicit; artifact redistribution still needs confirmation. |
| Silent-FAS source/checkpoints | Apache-2.0 repository | Source license is visible; checkpoint-specific and dataset-derived rights are not established. |
| CelebA-Spoof dataset/derived data | Official dataset agreement | Non-commercial research only; no further copy/publish/distribute of dataset or derived data, except internal same-site copies. |

## 7. Maintainer clarification questions

### A. OMZ / original anti-spoof-mn3 maintainer

1. Does the MIT license linked by the OMZ `anti-spoof-mn3` README cover the original trained checkpoint and the published/converted ONNX artifact, or only the source code?
2. May a university student use the checkpoint locally for a non-commercial FYP, private webcam testing, supervisor/evaluator demonstration, and private academic submission?
3. May the project publish integration code, preprocessing documentation, and benchmark results while linking to the authoritative model source without bundling the weights?
4. May the original or converted ONNX weights be included in a public GitHub repository, Release, or downloadable ZIP?
5. Does the CelebA-Spoof agreement impose additional restrictions on the trained or converted weights, and if so, what attribution or distribution conditions apply?

### B. Facenox MiniFASNetV2-SE maintainer

1. What license specifically covers `best_model.pth`, `best_model.onnx`, and `best_model_quantized.onnx`?
2. What is the exact output index mapping for Real and Spoof for each published artifact?
3. Does the license permit private non-commercial university evaluation and supervisor review?
4. Does it permit redistribution in public GitHub Releases or application ZIPs?
5. What dataset and pretrained components are included in the provenance chain, and do they impose additional restrictions?

### C. CelebA-Spoof maintainers

1. Does “derived data” in the agreement include trained neural-network weights or converted ONNX artifacts trained on the dataset?
2. Is private local use and a private non-commercial university demonstration permitted without a separate agreement?
3. May derived weights be shared privately with a supervisor/evaluator or included in a private academic submission?
4. May derived weights be redistributed publicly, including via GitHub Releases or an application package?

## 8. Recommended publication strategy

Until written clarification exists:

1. Publish Otto source code, interfaces, schemas, and preprocessing code only.
2. Keep model binaries out of Git history, Releases, ZIPs, containers, and installers.
3. Provide a documented configuration variable and an optional local model path, without committing a model file.
4. Link users to the original authoritative download page rather than mirroring a binary.
5. Include a `THIRD_PARTY_NOTICES` entry for every source repository and a separate note that model-weight/dataset rights must be checked by the user.
6. Do not commit CelebA-Spoof images, annotations, crops, pseudo-labels, or derived data.
7. Do not publish personal webcam frames, face crops, embeddings, or security logs.

This strategy does not itself grant model-use rights; it reduces redistribution risk while confirmation is pending.

## 9. Next phase recommendation

Do not select a production PAD model yet. The next phase should be a rights-gated, isolated artifact-verification phase for **OMZ anti-spoof-mn3 first**, with Facenox as a secondary candidate only if its maintainer confirms the weight license and mapping.

The verification phase should occur only after rights confirmation and should check, outside the project:

- exact artifact source, checksum, and license notices;
- input preprocessing and output-index mapping;
- CPU inference and OpenCV 5 loading;
- synthetic-input smoke behavior;
- no webcam, project integration, or public artifact redistribution.

## 10. Remaining uncertainties

- None of the reviewed sources gives a complete, unambiguous permission chain from training dataset to each candidate’s trained weights and converted ONNX files.
- CelebA-Spoof’s “derived data” wording is not interpreted here; rights-holder confirmation is required.
- Facenox’s exact output-index mapping and artifact-specific license were not independently verified.
- FeatherNet checkpoint terms and CASIA-SURF CeFA rights were not established.
- CDCN documentation is explicitly research-only and has no verified OpenCV 5/ONNX deployment contract.
- Silent-FAS artifact mappings and checkpoint rights remain unresolved.
- No candidate was downloaded, installed, executed, or tested on this project’s hardware.

## Final status

**PARTIAL** — public source-code licensing is documented for several candidates, but no candidate is fully cleared for the intended trained-weight use and public redistribution activities. Written rights-holder confirmation is required before model artifact use beyond carefully controlled, private evaluation.

