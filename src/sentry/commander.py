"""Serial interface for sending commands to the Arduino."""

from __future__ import annotations

import logging

import serial

logger = logging.getLogger(__name__)

# Angle limits - must match sentry.h
_PAN_MIN: int = 0
_PAN_MAX: int = 359
_TILT_MIN: int = 0
_TILT_MAX: int = 180


class Commander:
    """Context manager that owns the serial connection to the Arduino.

    All commands are newline-terminated ASCII, matching the firmware protocol:
        ``F\\n``        - activate relay (FIRE)
        ``S\\n``        - deactivate relay (SAFE)
        ``P<deg>\\n``   - set pan  angle, 0-359 degrees
        ``T<deg>\\n``   - set tilt angle, 0-180 degrees

    Args:
        port: Serial port the Arduino is connected to (e.g. ``/dev/ttyACM0``).
        baudrate: Baud rate - must match ``monitor_speed`` in ``platformio.ini``.
    """

    def __init__(self, port: str, baudrate: int = 115_200) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None

    def __enter__(self) -> Commander:
        self._serial = serial.Serial(self._port, self._baudrate, timeout=1)
        logger.debug("Serial port %s opened at %d baud.", self._port, self._baudrate)
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    # Public API

    def fire(self) -> None:
        """Send the FIRE command - activates the relay."""
        self._writeline(b"F")

    def safe(self) -> None:
        """Send the SAFE command - deactivates the relay."""
        self._writeline(b"S")

    def pan(self, degrees: int) -> None:
        """Set the pan servo angle.

        Args:
            degrees: Target angle in degrees, clamped to 0-359.
        """
        degrees = max(_PAN_MIN, min(_PAN_MAX, degrees))
        self._writeline(f"P{degrees}".encode())

    def tilt(self, degrees: int) -> None:
        """Set the tilt servo angle.

        Args:
            degrees: Target angle in degrees, clamped to 0-180.
        """
        degrees = max(_TILT_MIN, min(_TILT_MAX, degrees))
        self._writeline(f"T{degrees}".encode())

    def close(self) -> None:
        """Send SAFE, then close the serial port."""
        self.pan(180)
        self.safe()
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            logger.debug("Serial port %s closed.", self._port)

    # Internal

    def _writeline(self, cmd: bytes) -> None:
        """Write a newline-terminated command to the serial port."""
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Commander is not open - use it as a context manager.")
        self._serial.write(cmd + b"\n")
