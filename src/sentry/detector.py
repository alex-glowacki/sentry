"""Object detection interface - stub ready for Hailo SDK integration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Detection:
    """A single detection result from the inference pipeline.

    Attributes:
        label: Class label string (e.g. ``"person"``).
        confidence: Detection confidence in ``[0.0, 1.0]``.
        bbox: Bounding box as ``(x, y, width, height)`` in pixel coordinates.
    """

    label: str
    confidence: float
    bbox: tuple[int, int, int, int]


class Detector:
    """Wraps the Hailo inference pipeline and yields ``Detection`` objects.

    This is currently a stub. Replace the body of ``detect()`` with real
    Hailo SDK calls once the pipeline is validated.
    """

    def detect(self, frame: object) -> list[Detection]:
        """Run inference on *frame* and return a list of detections.

        Args:
            frame: A camera frame - type will be narrowed once the Hailo
                SDK is integrated (likely ``numpy.ndarray``).

        Returns:
            List of ``Detection`` objects. Returns empty list until
            the Hailo SDK is wired in.
        """
        # TODO: integrate Hailo SDK inference here
        return []
