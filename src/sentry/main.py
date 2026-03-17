"""CLI entry point for the Sentry targeting loop."""

from __future__ import annotations

import argparse
import logging
import sys

from sentry.commander import Commander
from sentry.detector import Detection, Detector


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sentry - AI-powered airsoft turret targeting loop."
    )
    parser.add_argument("--port", default="/dev/ttyACM0", help="Arduino serial port")
    parser.add_argument("--baudrate", type=int, default=115200, help="Serial baud rate")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Minimum confidence to trigger a fire command",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    log = logging.getLogger(__name__)

    detector = Detector()

    try:
        with Commander(port=args.port, baudrate=args.baudrate) as cmd:
            log.info("Sentry online - port=%s threshold=%.2f", args.port, args.threshold)
            # TODO: replace with real camera frame loop
            while True:
                frame = None  # placeholder until Hailo pipeline is wired in
                detections: list[Detection] = detector.detect(frame)

                high_conf = [d for d in detections if d.confidence >= args.threshold]

                if high_conf:
                    log.debug("Target acquired: %s", high_conf[0])
                    cmd.fire()
                else:
                    cmd.safe()

    except KeyboardInterrupt:
        log.info("Shutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
