"""Manual hardware integration test - relay and solenoid.

Run on the Pi with the Arduino connected:

    pytest tests/test_relay_hardware.py -v -s -m hardware

Requires:
    - Arduino flashed and connected on /dev/ttyACM0
    - PCA9685 wired to Arduino via I2C
    - Relay module wired to PCA9685 CH2
    - Solenoid wired to relay NO/COM
"""

from __future__ import annotations

import time
from collections.abc import Generator

import pytest

from sentry.commander import Commander

PORT = "/dev/ttyACM0"
BURST_S = 0.25
COOLDOWN_S = 0.5


@pytest.fixture()
def cmd() -> Generator[Commander, None, None]:
    """Open a Commander connection for the duration of the test."""
    with Commander(port=PORT) as commander:
        yield commander


@pytest.mark.hardware
def test_relay_fires_and_safes(cmd: Commander) -> None:
    """Relay should click ON then OFF; solenoid should actuate and retract."""
    cmd.fire()
    time.sleep(BURST_S)
    cmd.safe()


@pytest.mark.hardware
def test_relay_safe_on_close() -> None:
    """Commander.__exit__ must send SAFE before closing the port."""
    with Commander(port=PORT) as commander:
        commander.fire()
        time.sleep(BURST_S)
    # If we reach here without hanging, SAFE was sent on exit.


@pytest.mark.hardware
def test_burst_cooldown_cycle(cmd: Commander) -> None:
    """Three full burst/cooldown cycles - checks relay doesn't stick."""
    for _ in range(3):
        cmd.fire()
        time.sleep(BURST_S)
        cmd.safe()
        time.sleep(COOLDOWN_S)
