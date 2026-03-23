"""CLI entry point for the Sentry targeting loop."""

from __future__ import annotations

import argparse
import logging
import sys

from picamera2 import Picamera2  # type: ignore[import-untyped]

from sentry.commander import Commander
from sentry.detector import Detection, ObjectDetector

logger = logging.getLogger(__name__)

_FRAME_SIZE: tuple[int, int] = (640, 640)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sentry - AI-powered airsoft turret targeting loop."
    )
    parser.add_argument("--port", default="/dev/ttyACM0", help="Arduino serial port")
    parser.add_argument("--baudrate", type=int, default=115_200, help="Serial baud rate")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Minimum confidence to trigger a fire command",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def _build_camera() -> Picamera2:
    """Initialize and start the IMX708 camera at 640x640 RGB888."""
    logging.getLogger("picamera2").setLevel(logging.WARNING)
    cam = Picamera2()
    cam.configure(cam.create_preview_configuration(main={"format": "RGB888", "size": _FRAME_SIZE}))
    cam.start()
    logger.info("Camera started (%dx%d RGB888).", *_FRAME_SIZE)
    return cam


def main() -> None:
    """Run the Sentry targeting loop."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    cam = _build_camera()

    try:
        with (
            ObjectDetector(
                confidence_threshold=args.threshold,
            ) as detector,
            Commander(port=args.port, baudrate=args.baudrate) as cmd,
        ):
            logger.info("Sentry online - port=%s threshold=%.2f", args.port, args.threshold)
            while True:
                frame = cam.capture_array()
                detections: list[Detection] = detector.detect(frame)
                if detections:
                    best: Detection = max(detections, key=lambda d: d.confidence)
                    logger.debug("Target acquired: %s conf=%.2f", best.label, best.confidence)
                    cmd.fire()
                else:
                    cmd.safe()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        cam.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
