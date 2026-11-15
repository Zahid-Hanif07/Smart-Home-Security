import numpy as np
import torch
import onnxruntime as ort
from pathlib import Path

BASE = Path(__file__).resolve().parent
MODEL = BASE.parent / "faceocc.onnx"

print("Loading ONNX Runtime...")
session = ort.InferenceSession(
    str(MODEL),
    providers=["CPUExecutionProvider"]
)

print("Creating test input...")
np.random.seed(42)
test_input = np.random.randn(1, 3, 256, 256).astype(np.float32)

print("Running ONNX inference...")
result = session.run(["logits"], {"input": test_input})[0]

print("Output shape:", result.shape)
print("Output dtype:", result.dtype)
print("Output finite:", bool(np.isfinite(result).all()))
print("Logits min/max:", float(result.min()), float(result.max()))

print("\nChecking PyTorch reference...")
import segmentation_models_pytorch as smp
from safetensors.torch import load_file

model = smp.Unet(
    encoder_name="resnet18",
    encoder_weights=None,
    in_channels=3,
    classes=1,
)
model.load_state_dict(load_file(str(BASE / "model.safetensors")), strict=True)
model.eval()

with torch.no_grad():
    reference = model(torch.from_numpy(test_input)).numpy()

difference = np.abs(reference - result)
print("PyTorch shape:", reference.shape)
print("Maximum absolute difference:", float(difference.max()))
print("Mean absolute difference:", float(difference.mean()))

if result.shape != (1, 1, 256, 256):
    raise RuntimeError("Unexpected ONNX output shape")
if not np.isfinite(result).all():
    raise RuntimeError("ONNX output contains NaN or Inf")
if not np.allclose(reference, result, rtol=1e-3, atol=1e-4):
    raise RuntimeError("PyTorch and ONNX outputs do not match")

print("\nONNX RUNTIME VALIDATION: PASS")
