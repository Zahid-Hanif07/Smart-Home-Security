import unittest
import tempfile
from unittest.mock import patch

import cv2
import numpy as np

from app.security.face_occlusion_service import FaceOcclusionService


class FakeNet:
    def __init__(self, output):
        self.output = output
        self.input = None

    def setPreferableBackend(self, _backend):
        pass

    def setPreferableTarget(self, _target):
        pass

    def setInput(self, value):
        self.input = value

    def forward(self):
        return self.output


def service_with_output(output):
    with tempfile.NamedTemporaryFile(suffix=".onnx") as model_file:
        with patch("app.security.face_occlusion_service.cv2.dnn.readNetFromONNX", return_value=FakeNet(output)):
            service = FaceOcclusionService(model_file.name)
    return service


class TestFaceOcclusionService(unittest.TestCase):
    crop = np.full((64, 80, 3), 128, dtype=np.uint8)

    def test_missing_model_is_explicit(self):
        result = FaceOcclusionService("missing-faceocc.onnx").evaluate(self.crop)
        self.assertEqual(result.state, "model_unavailable")
        self.assertEqual(result.reason, "model_file_missing")

    def test_model_loading_failure_is_explicit(self):
        with tempfile.NamedTemporaryFile(suffix=".onnx") as model_file:
            with patch(
                "app.security.face_occlusion_service.cv2.dnn.readNetFromONNX",
                side_effect=RuntimeError("bad graph"),
            ):
                service = FaceOcclusionService(model_file.name)
        self.assertEqual(service.evaluate(self.crop).state, "model_unavailable")
        self.assertIn("model_load_failed", service.load_error)

    def test_valid_input_returns_segmentation_statistics(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        result = service.evaluate(self.crop)
        self.assertEqual(result.state, "segmentation_available")
        self.assertEqual(result.output_dimensions, (1, 1, 256, 256))
        self.assertEqual(result.probability_map.shape, (1, 1, 256, 256))
        self.assertEqual(result.binary_mask.dtype, np.uint8)
        self.assertAlmostEqual(result.visible_ratio, 1.0)
        self.assertAlmostEqual(result.mean_probability, 0.5)
        self.assertAlmostEqual(result.near_threshold_fraction, 1.0)

    def test_preprocessing_is_bgr_rgb_float32_nchw(self):
        prepared = FaceOcclusionService._preprocess(
            np.array([[[0, 0, 255]]], dtype=np.uint8).repeat(20, 0).repeat(20, 1)
        )
        self.assertEqual(prepared.shape, (1, 3, 256, 256))
        self.assertEqual(prepared.dtype, np.float32)
        self.assertGreater(float(prepared[0, 0].mean()), 1.0)
        self.assertTrue(np.all(np.isfinite(prepared)))
        np.testing.assert_array_equal(prepared, FaceOcclusionService._preprocess(
            np.array([[[0, 0, 255]]], dtype=np.uint8).repeat(20, 0).repeat(20, 1)
        ))

    def test_invalid_and_tiny_inputs_are_rejected(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        self.assertEqual(service.evaluate(None).state, "not_evaluated")
        for crop in (np.empty((0, 0, 3), dtype=np.uint8), np.zeros((8, 8, 3), dtype=np.uint8)):
            self.assertEqual(service.evaluate(crop).state, "invalid_input")
        self.assertEqual(service.evaluate(np.zeros((32, 32), dtype=np.uint8)).state, "invalid_input")
        self.assertEqual(service.evaluate(np.zeros((32, 32, 4), dtype=np.uint8)).state, "invalid_input")

    def test_invalid_mode_and_face_state_are_explicit(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        self.assertEqual(service.evaluate(self.crop, mode="other").state, "invalid_input")
        self.assertEqual(service.evaluate(self.crop, face_detected=False).state, "face_not_detected")
        self.assertEqual(
            service.evaluate(self.crop, quality={"quality": "uncertain", "reason": "blur"}).state,
            "poor_quality",
        )

    def test_output_shape_and_non_finite_output_fail_safely(self):
        wrong_shape = service_with_output(np.zeros((1, 256, 256), dtype=np.float32))
        self.assertEqual(wrong_shape.evaluate(self.crop).state, "inference_failed")
        non_finite = service_with_output(np.full((1, 1, 256, 256), np.inf, dtype=np.float32))
        self.assertEqual(non_finite.evaluate(self.crop).state, "inference_failed")

    def test_sigmoid_is_stable_for_large_logits(self):
        service = service_with_output(
            np.array([[[[-1000.0, 1000.0]]]], dtype=np.float32).repeat(256, 2).repeat(128, 3)
        )
        result = service.evaluate(self.crop)
        self.assertEqual(result.state, "segmentation_available")
        self.assertTrue(np.all(np.isfinite(result.probability_map)))

    def test_landmark_alignment_is_explicitly_selectable(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        landmarks = np.array([[20, 15], [60, 15], [40, 30], [22, 50], [58, 50]], dtype=np.float32)
        result = service.evaluate(self.crop, mode="landmark_aligned", landmarks=landmarks)
        self.assertEqual(result.state, "segmentation_available")
        self.assertEqual(result.mode, "landmark_aligned")

    def test_alignment_does_not_fall_back_to_direct_crop(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        missing = service.evaluate(self.crop, mode="landmark_aligned")
        invalid = service.evaluate(self.crop, mode="landmark_aligned", landmarks=[[1, 2]])
        self.assertEqual(missing.state, "uncertain")
        self.assertEqual(missing.reason, "landmarks_unavailable_for_alignment")
        self.assertEqual(invalid.state, "uncertain")
        self.assertEqual(invalid.reason, "invalid_landmarks")

    def test_alignment_rejects_duplicate_and_nearly_duplicate_landmarks(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        duplicate = np.array([[20, 15], [20, 15], [40, 30], [22, 50], [58, 50]], dtype=np.float32)
        nearly_duplicate = np.array([[20, 15], [20.5, 15], [40, 30], [22, 50], [58, 50]], dtype=np.float32)
        self.assertEqual(
            service.evaluate(self.crop, mode="landmark_aligned", landmarks=duplicate).reason,
            "landmarks_nearly_duplicate",
        )
        self.assertEqual(
            service.evaluate(self.crop, mode="landmark_aligned", landmarks=nearly_duplicate).reason,
            "landmarks_nearly_duplicate",
        )

    def test_alignment_rejects_non_numeric_non_finite_out_of_bounds_and_degenerate_landmarks(self):
        service = service_with_output(np.zeros((1, 1, 256, 256), dtype=np.float32))
        cases = [
            ([['a', 1], [60, 15], [40, 30], [22, 50], [58, 50]], "invalid_landmarks"),
            ([[np.nan, 15], [60, 15], [40, 30], [22, 50], [58, 50]], "invalid_landmarks"),
            ([[20, 15], [80, 15], [40, 30], [22, 50], [58, 50]], "landmarks_outside_crop"),
            ([[10, 20], [20, 20], [30, 20], [40, 20], [50, 20]], "landmarks_degenerate"),
        ]
        for landmarks, reason in cases:
            result = service.evaluate(self.crop, mode="landmark_aligned", landmarks=landmarks)
            self.assertEqual(result.state, "uncertain")
            self.assertEqual(result.reason, reason)


if __name__ == "__main__":
    unittest.main()
