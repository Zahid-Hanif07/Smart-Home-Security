# Model licenses draft

Model rights are component-specific. A repository license for source code does not automatically license pretrained weights, converted ONNX files, or training data.

## Current policy

Do not commit, bundle, mirror, or publish PAD weights until the exact artifact license and training-data restrictions are confirmed in writing. Configure local model paths instead.

## Existing model families

- YuNet and SFace: record the exact artifact source, license, notices, and redistribution terms before public release.
- FaceOcc: record the checkpoint source, conversion provenance, license, and dataset restrictions; keep the current artifact outside Git until reviewed.
- OMZ `anti-spoof-mn3`: technically documented, but CelebA-Spoof-derived weight redistribution remains unresolved.
- Facenox MiniFASNetV2-SE: artifact license and exact class mapping require maintainer confirmation.
- FeatherNet, CDCN, and Silent-Face variants: checkpoint-specific rights and provenance are not fully established.

## Required record for each binary

Artifact URL, checksum, model version, input contract, output mapping, source-code license, weight license, dataset license, attribution text, and permitted distribution modes.

See the Phase 8.0.6 and 8.0.7 inquiry records before using a candidate in a public release.

