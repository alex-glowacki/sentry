"""CLI entry point for the Sentry targeting loop."""

from __future__ import annotations

import argparse
import logging
import time

from picamera2 import Picamera2

from sentry.commander import Commander
from sentry.detector import Detection, ObjectDetector
from sentry.preview import PreviewStreamer

logger = logging.getLogger(__name__)

_FRAME_SIZE: tuple[int, int] = (640, 640)
_DEFAULT_TARGETS: str = "person"

_PAN_CENTER: int = 90  # degrees - mid of 0-270
_TILT_CENTER: int = 90  # degrees - mid of 0-180
_PAN_BIAS: int = 0  # tune empirically - positive = right
_TILT_BIAS: int = 0  # tune empirically - positive = down (camera above barrel)


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
        default=100,
        help="Duration in milliseconds to hold the relay open per burst (default: 250)",
    )
    parser.add_argument(
        "--cooldown-ms",
        type=int,
        default=600,
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
    parser.add_argument(
        "--pan-dead",
        type=float,
        default=2.0,
        help="Pan dead-zone in degrees — suppress servo movement within this threshold"
        " (default: 2)",
    )
    parser.add_argument(
        "--tilt-dead",
        type=float,
        default=2.0,
        help="Tilt dead-zone in degrees — suppress servo movement within this threshold"
        " (default: 2)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Stream an annotated MJPEG preview at http://sentry.local:8080",
    )
    parser.add_argument(
        "--preview-port",
        type=int,
        default=8080,
        help="Port for the MJPEG preview server (default: 8080)",
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
    """Compute absolute pan/tilt angles to centre on a detection."""
    y1, x1, y2, x2 = detection.bbox

    cx: float = (x1 + x2) - 1.0
    cy: float = (y1 + y2) - 1.0

    pan_deg: int = round(_PAN_CENTER + cx * pan_range) + _PAN_BIAS
    tilt_deg: int = round(_TILT_CENTER + cy * tilt_range) + _TILT_BIAS

    return pan_deg, tilt_deg


def _in_dead_zone(
    pan_deg: int,
    tilt_deg: int,
    last_pan: int,
    last_tilt: int,
    pan_dead: float,
    tilt_dead: float,
) -> bool:
    """Return True if the requested position is within the dead-zone."""
    return abs(pan_deg - last_pan) <= pan_dead and abs(tilt_deg - last_tilt) <= tilt_dead


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
        "Targets: %s | burst=%dms cooldown=%dms | pan_range=%.1f tilt_range=%.1f"
        " | pan_dead=%.1f tilt_dead=%.1f",
        ", ".join(sorted(targets)),
        args.burst_ms,
        args.cooldown_ms,
        args.pan_range,
        args.tilt_range,
        args.pan_dead,
        args.tilt_dead,
    )

    cam = _build_camera()

    previewer: PreviewStreamer | None = None
    if args.preview:
        previewer = PreviewStreamer(port=args.preview_port, frame_size=_FRAME_SIZE)
        previewer.start()

    burst_end: float = 0.0
    cooldown_end: float = 0.0
    _firing: bool = False
    _pan_moving: bool = False

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

                if now < burst_end:
                    continue

                if burst_end != 0.0 and now < cooldown_end:
                    if _firing:
                        cmd.safe()
                        _firing = False
                        _pan_moving = False
                    continue

                if now < cooldown_end:
                    continue

                frame = cam.capture_array()
                detections: list[Detection] = detector.detect(frame)
                engaged = [d for d in detections if d.label.lower() in targets]

                pan_deg: int | None = None
                tilt_deg: int | None = None

                if engaged:
                    best: Detection = max(engaged, key=lambda d: d.confidence)
                    pan_deg, tilt_deg = _aim(best, args.pan_range, args.tilt_range)

                    if not _in_dead_zone(
                        pan_deg, tilt_deg, *cmd.position, args.pan_dead, args.tilt_dead
                    ):
                        cmd.pan(pan_deg)
                        cmd.tilt(tilt_deg)
                        _pan_moving = True
                        logger.debug(
                            "Servo update: pan=%d tilt=%d",
                            pan_deg,
                            tilt_deg,
                        )

                    if not _firing:
                        cmd.fire()
                        _firing = True

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
                    burst_end = now + burst_s
                    cooldown_end = burst_end + cooldown_s
                else:
                    if _firing or _pan_moving:
                        cmd.safe()
                        _firing = False
                        _pan_moving = False

                if previewer is not None:
                    last_pan, last_tilt = cmd.position
                    previewer.push(
                        frame,
                        detections,
                        engaged,
                        pan_deg,
                        tilt_deg,
                        last_pan,
                        last_tilt,
                        args.pan_dead,
                        args.tilt_dead,
                        args.pan_range,
                        args.tilt_range,
                    )

    except KeyboardInterrupt:
        logger.info("Shutting down.")
    finally:
        cam.stop()
        if previewer is not None:
            previewer.stop()


if __name__ == "__main__":
    main()
