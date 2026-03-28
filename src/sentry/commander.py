"""Serial interface for sending commands to the Arduino."""

from __future__ import annotations

import logging
import time

import serial

logger = logging.getLogger(__name__)

# Angle limits - must match sentry.h
_PAN_MIN: int = 0
_PAN_MAX: int = 270
_TILT_MIN: int = 0
_TILT_MAX: int = 180

# Slew rate - degrees per step, one step per _writeline sleep (50 Hz max).
# Smaller = smoother; 2° at 50 Hz gives ~25°/s slew rate.
_SLEW_STEP_DEG: int = 2


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

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self._port = port
        self._baudrate = baudrate
        self._serial: serial.Serial | None = None
        self._pan: int = _PAN_MIN + (_PAN_MAX - _PAN_MIN) // 2  # 179
        self._tilt: int = _TILT_MIN + (_TILT_MAX - _TILT_MIN) // 2  # 90

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
        """Set the pan servo angle immediately (no slewing).

        Args:
            degrees: Target angle in degrees, clamped to 0-359.
        """
        degrees = max(_PAN_MIN, min(_PAN_MAX, degrees))
        self._writeline(f"P{degrees}".encode())
        self._pan = degrees

    def tilt(self, degrees: int) -> None:
        """Set the tilt servo angle immediately (no slewing).

        Args:
            degrees: Target angle in degrees, clamped to 0-180.
        """
        degrees = max(_TILT_MIN, min(_TILT_MAX, degrees))
        self._writeline(f"T{degrees}".encode())
        self._tilt = degrees

    @property
    def position(self) -> tuple[int, int]:
        """Current commanded position as ``(pan_deg, tilt_deg)``."""
        return self._pan, self._tilt

    def slew_to(self, pan: int, tilt: int) -> None:
        """Smoothly slew both axes toward the target angle.

        Steps both pan and tilt simultaneously by up to ``_SLEW_STEP_DEG``
        per iteration until both axes reach their targets. Each step is rate-
        limited by the sleep in ``_writeline``, giving a maximum slew rate of
        ``_SLEW_STEP_DEG * 50`` degrees per second.

        Args:
            pan: Target pan angle in degrees, clamped to 0-359.
            tilt: Target tilt angle in degrees, clamped to 0-180.
        """
        pan = max(_PAN_MIN, min(_PAN_MAX, pan))
        tilt = max(_TILT_MIN, min(_TILT_MAX, tilt))

        while self._pan != pan or self._tilt != tilt:
            next_pan = _step_toward(self._pan, pan, _SLEW_STEP_DEG)
            next_tilt = _step_toward(self._tilt, tilt, _SLEW_STEP_DEG)

            if next_pan != self._pan:
                self.pan(next_pan)
            if next_tilt != self._tilt:
                self.tilt(next_tilt)

    def close(self) -> None:
        """Slew to center, send SAFE, then close the serial port."""
        self.slew_to(
            _PAN_MIN + (_PAN_MAX - _PAN_MIN) // 2,
            _TILT_MIN + (_TILT_MAX - _TILT_MIN) // 2,
        )
        self.safe()
        time.sleep(0.1)
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
            logger.debug("Serial port %s closed.", self._port)

    # Internal

    def _writeline(self, cmd: bytes) -> None:
        """Write a newline-terminated command to the serial port."""
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Commander is not open - use it as a context manager.")
        self._serial.write(cmd + b"\n")
        time.sleep(0.02)


def _step_toward(current: int, target: int, step: int) -> int:
    """Advance ``current`` toward ``target`` by at most ``step`` degrees.

    Args:
        current: Current angle in degrees.
        target: Desired angle in degrees.
        step: Maximum step size in degrees.

    Returns:
        New angle, clamped to ``target`` if within one step.
    """
    if current < target:
        return min(current + step, target)
    if current > target:
        return max(current - step, target)
    return current
