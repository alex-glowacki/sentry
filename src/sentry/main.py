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

_PAN_CENTER: int = 180  # degrees — mid of 0–359
_TILT_CENTER: int = 90  # degrees — mid of 0–180


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
            "Example: --targets person,dog"
        ),
    )
    parser.add_argument(
        "--pan-range",
        type=float,
        default=90.0,
        help=(
            "Half-sweep of pan in degrees — maps frame edge to this"
            " offset from center (default: 90)"
        ),
    )
    parser.add_argument(
        "--tilt-range",
        type=float,
        default=45.0,
        help=(
            "Half-sweep of tilt in degrees — maps frame edge to this"
            " offset from center (default: 45)"
        ),
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def _parse_targets(raw: str) -> frozenset[str]:
    """Parse a comma-separated targets string into a frozenset of lowercase labels."""
    return frozenset(label.strip().lower() for label in raw.split(",") if label.strip())


def _aim(
    detection: Detection,
    pan_range: float,
    tilt_range: float,
) -> tuple[int, int]:
    """Compute absolute pan/tilt angles to centre on a detection.

    Normalises the bounding box centre to [-1, 1] relative to the frame,
    then scales by the configured range and offsets from the servo centre.

    Args:
        detection: Detection whose bbox to aim at.
        pan_range: Half-sweep in degrees for pan (maps frame edge → ±pan_range).
        tilt_range: Half-sweep in degrees for tilt (maps frame edge → ±tilt_range).

    Returns:
        ``(pan_deg, tilt_deg)`` as absolute integer degrees.
    """
    y1, x1, y2, x2 = detection.bbox

    # Bbox centre, normalised to [-1, 1] (0,0 = frame centre).
    cx: float = (x1 + x2) - 1.0  # equiv. to (centre_x / 0.5) - 1
    cy: float = (y1 + y2) - 1.0

    pan_deg: int = round(_PAN_CENTER + cx * pan_range)
    tilt_deg: int = round(_TILT_CENTER + cy * tilt_range)

    return pan_deg, tilt_deg


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

    targets: frozenset[str] = _parse_targets(args.targets)
    burst_s: float = args.burst_ms / 1_000.0
    cooldown_s: float = args.cooldown_ms / 1_000.0

    logger.info(
        "Targets: %s | burst=%dms cooldown=%dms | pan_range=%.1f tilt_range=%.1f",
        ", ".join(sorted(targets)),
        args.burst_ms,
        args.cooldown_ms,
        args.pan_range,
        args.tilt_range,
    )

    cam = _build_camera()

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

                # --- Burst just ended: send SAFE and wait out cooldown. ---
                if burst_end != 0.0 and now < cooldown_end:
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
                    pan_deg, tilt_deg = _aim(best, args.pan_range, args.tilt_range)

                    cmd.pan(pan_deg)
                    cmd.tilt(tilt_deg)

                    logger.debug(
                        "Target acquired: %s conf=%.2f bbox=%s"
                        " → pan=%d tilt=%d — firing burst (%dms)",
                        best.label,
                        best.confidence,
                        best.bbox,
                        pan_deg,
                        tilt_deg,
                        args.burst_ms,
                    )
                    cmd.fire()
                    burst_end = now + burst_s
                    cooldown_end = burst_end + cooldown_s
                else:
                    cmd.pan(180)
                    cmd.safe()

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        cam.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
