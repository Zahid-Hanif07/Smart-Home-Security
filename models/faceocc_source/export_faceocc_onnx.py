import torch
import onnx
import segmentation_models_pytorch as smp
from safetensors.torch import load_file
from pathlib import Path

BASE = Path(__file__).resolve().parent
CHECKPOINT = BASE / "model.safetensors"
OUTPUT = BASE.parent / "faceocc.onnx"

print("Loading FaceOcc architecture...")

model = smp.Unet(
    encoder_name="resnet18",
    encoder_weights=None,
    in_channels=3,
    classes=1,
)

print("Loading official checkpoint...")
state_dict = load_file(str(CHECKPOINT))
model.load_state_dict(state_dict, strict=True)
model.eval()

dummy_input = torch.randn(1, 3, 256, 256)

print("Exporting ONNX...")
with torch.no_grad():
    torch.onnx.export(
        model,
        dummy_input,
        str(OUTPUT),
        input_names=["input"],
        output_names=["logits"],
        opset_version=17,
        do_constant_folding=True,
        dynamo=False,
    )

print("Checking ONNX model...")
onnx_model = onnx.load(str(OUTPUT))
onnx.checker.check_model(onnx_model)

print("SUCCESS")
print("Output:", OUTPUT)
print("Input:", onnx_model.graph.input[0].name)
print("Output:", onnx_model.graph.output[0].name)
print("Size:", OUTPUT.stat().st_size, "bytes")
