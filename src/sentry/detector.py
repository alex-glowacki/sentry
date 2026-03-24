"""detector.py — Object detection via the Hailo AI HAT+ 2.

Wraps the HailoRT Python API to run YOLOv8m inference on the HAILO10H chip.
Frames are supplied by the caller (e.g. from picamera2); this module is
responsible only for inference and result parsing.

NMS output buffer layout (yolov8m_h10.hef):
    shape  : (40080,) float32
    layout : 80 classes × 501 floats
               [0]      — number of detections for this class (float, cast to int)
               [1..500] — up to 100 proposals of (y1, x1, y2, x2, score)
                          coordinates are normalised to [0.0, 1.0]
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Final

import numpy as np
from hailo_platform import VDevice

logger = logging.getLogger(__name__)

# Path to the HEF compiled for the HAILO10H (H10) chip.
DEFAULT_HEF: Final[str] = "/usr/share/hailo-models/yolov8m_h10.hef"

# COCO class labels (80 classes, indices match YOLOv8 output order).
COCO_LABELS: Final[tuple[str, ...]] = (
    "person",
    "bicycle",
    "car",
    "motorcycle",
    "airplane",
    "bus",
    "train",
    "truck",
    "boat",
    "traffic light",
    "fire hydrant",
    "stop sign",
    "parking meter",
    "bench",
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
    "backpack",
    "umbrella",
    "handbag",
    "tie",
    "suitcase",
    "frisbee",
    "skis",
    "snowboard",
    "sports ball",
    "kite",
    "baseball bat",
    "baseball glove",
    "skateboard",
    "surfboard",
    "tennis racket",
    "bottle",
    "wine glass",
    "cup",
    "fork",
    "knife",
    "spoon",
    "bowl",
    "banana",
    "apple",
    "sandwich",
    "orange",
    "broccoli",
    "carrot",
    "hot dog",
    "pizza",
    "donut",
    "cake",
    "chair",
    "couch",
    "potted plant",
    "bed",
    "dining table",
    "toilet",
    "tv",
    "laptop",
    "mouse",
    "remote",
    "keyboard",
    "cell phone",
    "microwave",
    "oven",
    "toaster",
    "sink",
    "refrigerator",
    "book",
    "clock",
    "vase",
    "scissors",
    "teddy bear",
    "hair drier",
    "toothbrush",
)

_NUM_CLASSES: Final[int] = 80
_MAX_PROPOSALS: Final[int] = 100
_FLOATS_PER_PROPOSAL: Final[int] = 5  # y1, x1, y2, x2, score
_STRIDE: Final[int] = _MAX_PROPOSALS * _FLOATS_PER_PROPOSAL + 1  # 501


@dataclass(frozen=True)
class Detection:
    """A single object detection result.

    Attributes:
        label: Human-readable COCO class label (e.g. ``"person"``).
        confidence: Detection confidence in ``[0.0, 1.0]``.
        bbox: Bounding box as ``(y1, x1, y2, x2)`` normalised to ``[0.0, 1.0]``.
    """

    label: str
    confidence: float
    bbox: tuple[float, float, float, float] = field(default=(0.0, 0.0, 0.0, 0.0))


def _parse_nms_buffer(
    buf: np.ndarray,
    confidence_threshold: float,
) -> list[Detection]:
    """Parse a flat NMS output buffer into :class:`Detection` objects.

    Args:
        buf: Float32 array of shape ``(40080,)`` as returned by the model.
        confidence_threshold: Discard detections below this score.

    Returns:
        List of detections above *confidence_threshold*, all classes combined.
    """
    results: list[Detection] = []
    view = buf.reshape(_NUM_CLASSES, _STRIDE)

    for class_idx in range(_NUM_CLASSES):
        n_det = int(view[class_idx, 0])
        if n_det == 0:
            continue
        proposals = view[class_idx, 1:].reshape(_MAX_PROPOSALS, _FLOATS_PER_PROPOSAL)
        for i in range(min(n_det, _MAX_PROPOSALS)):
            y1, x1, y2, x2, score = proposals[i]
            if score < confidence_threshold:
                continue
            results.append(
                Detection(
                    label=COCO_LABELS[class_idx],
                    confidence=float(score),
                    bbox=(float(y1), float(x1), float(y2), float(x2)),
                )
            )

    return results


class ObjectDetector:
    """Runs YOLOv8m inference on the Hailo AI HAT+ 2 (HAILO10H).

    The caller is responsible for supplying frames (e.g. via picamera2).
    Call :meth:`start` once before calling :meth:`detect`, and
    :meth:`stop` when finished.

    Args:
        confidence_threshold: Detections below this score are discarded.
        iou_threshold: NMS IoU threshold passed to the model.
        hef_path: Path to the compiled ``.hef`` model file.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        hef_path: str = DEFAULT_HEF,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.hef_path = hef_path

        self._vdevice: VDevice | None = None
        self._configured: Any | None = None  # ConfiguredInferModel (untyped SDK)
        self._output_buf: np.ndarray | None = None
        self._running = False

        logger.info(
            "ObjectDetector created (hef=%s, conf=%.2f, iou=%.2f)",
            hef_path,
            confidence_threshold,
            iou_threshold,
        )

    def start(self) -> None:
        """Open the Hailo device and load the model for inference."""
        logger.info("Starting Hailo inference pipeline…")
        self._vdevice = VDevice()
        model = self._vdevice.create_infer_model(self.hef_path)
        model.output().set_nms_score_threshold(self.confidence_threshold)
        model.output().set_nms_iou_threshold(self.iou_threshold)
        model.output().set_nms_max_proposals_per_class(_MAX_PROPOSALS)
        self._model = model
        self._configured = model.configure()
        self._configured.__enter__()
        self._bindings = self._configured.create_bindings()
        self._output_buf = np.empty(_NUM_CLASSES * _STRIDE, dtype=np.float32)
        self._bindings.output().set_buffer(self._output_buf)
        self._running = True
        logger.info("Hailo inference pipeline ready.")

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference on a single BGR/RGB frame and return detections.

        Args:
            frame: ``uint8`` numpy array of shape ``(640, 640, 3)``.
                   Resize to 640×640 before calling if needed.

        Returns:
            List of :class:`Detection` objects above the confidence threshold.

        Raises:
            RuntimeError: If :meth:`start` has not been called.
        """
        if not self._running or self._configured is None:
            raise RuntimeError("ObjectDetector.start() must be called before detect().")

        self._bindings.input().set_buffer(np.ascontiguousarray(frame))
        self._configured.run([self._bindings], timeout=5_000)
        assert self._output_buf is not None
        detections = _parse_nms_buffer(self._output_buf, self.confidence_threshold)
        logger.debug("Frame detections: %d", len(detections))
        return detections

    def stop(self) -> None:
        """Release the Hailo device and clean up resources."""
        if self._configured is not None:
            try:
                self._configured.__exit__(None, None, None)
            except Exception:
                logger.exception("Error closing ConfiguredInferModel.")
            self._configured = None
        self._vdevice = None
        self._running = False
        logger.info("Hailo inference pipeline stopped.")

    def __enter__(self) -> ObjectDetector:
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()
