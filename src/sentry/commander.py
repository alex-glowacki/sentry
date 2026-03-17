"""Serial interface for sending commands to the Arduino."""

from __future__ import annotations

import serial

CMD_FIRE: bytes = b"F"
CMD_SAFE: bytes = b"S"


class Commander:
    """Context manager that owns the serial connection to the Arduino.

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
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def fire(self) -> None:
        """Send the FIRE command - activates the relay."""
        self._write(CMD_FIRE)

    def safe(self) -> None:
        """Send the SAFE command - deactivates the relay."""
        self._write(CMD_SAFE)

    def close(self) -> None:
        """Send SAFE, then close the serial port."""
        self.safe()
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    def _write(self, cmd: bytes) -> None:
        if self._serial is None or not self._serial.is_open:
            raise RuntimeError("Commander is not open - use it as a context manager.")
        self._serial.write(cmd)
