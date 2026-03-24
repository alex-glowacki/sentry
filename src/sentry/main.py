"""CLI entry point for the Sentry targeting loop."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from picamera2 import Picamera2

from sentry.commander import Commander
from sentry.detector import Detection, ObjectDetector

logger = logging.getLogger(__name__)

_FRAME_SIZE: tuple[int, int] = (640, 640)

_DEFAULT_TARGETS: str = "person"


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
    parser.add_argument(
        "--burst-ms",
        type=int,
        default=250,
        help="Duration in milliseconds to hold the relay open per burst (default: 250)",
    )
    parser.add_argument(
        "--cooldown-ms",
        type=int,
        default=500,
        help="Lockout duration in milliseconds after a burst ends (default: 500)",
    )
    parser.add_argument(
        "--targets",
        default=_DEFAULT_TARGETS,
        help=(
            "Comma-separated list of COCO class labels to engage "
            f"(default: '{_DEFAULT_TARGETS}'). "
            "Example: --targest person,dog"
        ),
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


def _parse_targets(raw: str) -> frozenset[str]:
    """Parse a comma-separated targets string into a frozenset of lowercase labels."""
    return frozenset(label.strip().lower() for label in raw.split(",") if label.strip())


def main() -> None:
    """Run the Sentry targeting loop."""
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    targets: frozenset[str] = _parse_targets(args.targets)
    burst_s: float = args.burst_ms / 1_000.0
    cooldown_s: float = args.cooldown_ms / 1_000.0

    logger.info(
        "Targets: %s | burst=%dms cooldown=%dms",
        ", ".join(sorted(targets)),
        args.burst_ms,
        args.cooldown_ms,
    )

    cam = _build_camera()

    # Burst-fire state machine.
    # burst_end:    monotonic time when the current burst should stop firing.
    # cooldown_end: monotonic time when the cooldown lockout expires.
    burst_end: float = 0.0
    cooldown_end: float = 0.0

    try:
        with (
            ObjectDetector(confidence_threshold=args.threshold) as detector,
            Commander(port=args.port, baudrate=args.baudrate) as cmd,
        ):
            logger.info(
                "Sentry online - port=%s threshold=%.2f",
                args.port,
                args.threshold,
            )
            while True:
                now: float = time.monotonic()

                # --- Active burst: hold fire until burst window expires. ---
                if now < burst_end:
                    continue

                # --- Burst just ended: send SAFE and start cooldown. ---
                if burst_end != 0.0 and now >= burst_end and now < cooldown_end:
                    cmd.safe()
                    continue

                # --- Cooldown lockout: suppress all firing. ---
                if now < cooldown_end:
                    continue

                # --- Normal evaluation. ---
                frame = cam.capture_array()
                detections: list[Detection] = detector.detect(frame)

                engaged = [d for d in detections if d.label.lower() in targets]

                if engaged:
                    best: Detection = max(engaged, key=lambda d: d.confidence)
                    logger.debug(
                        "Target acquired: %s conf=%.2f — firing burst (%dms)",
                        best.label,
                        best.confidence,
                        args.burst_ms,
                    )
                    cmd.fire()
                    burst_end = now + burst_s
                    cooldown_end = burst_end + cooldown_s
                else:
                    cmd.safe()

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        cam.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
