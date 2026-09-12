"""Agent 1 — local person and pose detection.

The configured YOLO26 checkpoint was fine-tuned on C2A to detect people and
classify every detected bounding box as bent, kneeling, lying, sitting, or
upright.

This adapter reports visible posture only. It does not diagnose injuries,
determine urgency, or dispatch resources.
"""

from __future__ import annotations

import io
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List

from app.schemas.common import PoseLabel


_EXPECTED_CLASSES = {
    0: PoseLabel.bent,
    1: PoseLabel.kneeling,
    2: PoseLabel.lying,
    3: PoseLabel.sitting,
    4: PoseLabel.upright,
}


@dataclass(frozen=True)
class RawPoseDetection:
    pose: PoseLabel
    confidence: float


class YoloPoseDetector:
    """Lazy-loading wrapper around the local C2A pose checkpoint."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence_threshold: float | None = None,
        iou_threshold: float = 0.50,
        image_size: int = 640,
        device: str | None = None,
    ) -> None:

        backend_root = Path(__file__).resolve().parents[2]

        configured_path = (
            model_path
            or os.getenv("POSE_MODEL_PATH")
            or "weights/c2a-pose-best.pt"
        )

        candidate_path = Path(configured_path).expanduser()

        self.model_path = (
            candidate_path
            if candidate_path.is_absolute()
            else backend_root / candidate_path
        )

        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else float(os.getenv("POSE_CONFIDENCE_THRESHOLD", "0.10"))
        )

        self.iou_threshold = iou_threshold
        self.image_size = image_size
        self.device = device or os.getenv("POSE_DEVICE", "0")

        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                "POSE_CONFIDENCE_THRESHOLD must be between 0 and 1"
            )

        self._model = None
        self._lock = threading.Lock()

    def _load_model(self):
        if self._model is not None:
            return self._model

        if not self.model_path.is_file():
            raise FileNotFoundError(
                f"Pose checkpoint not found: {self.model_path}"
            )

        try:
            import torch
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "The pose-detector runtime requires torch and ultralytics"
            ) from exc

        # Required workaround for the GB10 container.
        torch.backends.cudnn.enabled = False
        torch.backends.cudnn.benchmark = False

        model = YOLO(str(self.model_path))

        expected_names = {
            class_id: pose.value
            for class_id, pose in _EXPECTED_CLASSES.items()
        }

        actual_names = {
            int(class_id): str(name).strip().lower()
            for class_id, name in model.names.items()
        }

        if actual_names != expected_names:
            raise RuntimeError(
                "Unexpected pose-model classes. "
                f"Expected {expected_names}, received {actual_names}"
            )

        self._model = model
        return model

    @staticmethod
    def _decode_image(image_bytes: bytes):
        if not image_bytes:
            raise ValueError("Image is empty")

        try:
            import numpy as np
            from PIL import Image

            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            return np.asarray(image)
        except ImportError as exc:
            raise RuntimeError(
                "The detector runtime requires numpy and Pillow"
            ) from exc
        except Exception as exc:
            raise ValueError(
                "Uploaded data is not a valid image"
            ) from exc

    def detect(self, image_bytes: bytes) -> List[RawPoseDetection]:
        image = self._decode_image(image_bytes)
        model = self._load_model()

        # FastAPI may handle multiple uploads concurrently, so serialize
        # access to this GPU model instance.
        with self._lock:
            results = model.predict(
                source=image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                imgsz=self.image_size,
                device=self.device,
                verbose=False,
            )

        detections: List[RawPoseDetection] = []

        for result in results:
            if result.boxes is None:
                continue

            for box in result.boxes:
                class_id = int(box.cls.item())
                pose = _EXPECTED_CLASSES.get(class_id)

                if pose is None:
                    raise RuntimeError(
                        f"Pose model returned unknown class ID {class_id}"
                    )

                detections.append(
                    RawPoseDetection(
                        pose=pose,
                        confidence=round(float(box.conf.item()), 6),
                    )
                )

        return detections


pose_detector = YoloPoseDetector()
