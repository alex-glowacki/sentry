#!/usr/bin/env python3
"""Burst duration tuning script - test motor timing without full stack."""

import time

from sentry.commander import Commander

PORT = "/dev/ttyACM0"
BURST_S = 0.1  # adjust this value to tune burst duration
CYCLES = 2  # number of cycles to test


def main() -> None:
    with Commander(port=PORT) as cmd:
        for i in range(CYCLES):
            print(f"Cycle {i + 1}/{CYCLES} - firing {BURST_S * 1000:.0f}ms burst...")
            cmd.fire()
            time.sleep(BURST_S)
            cmd.safe()
            print("Safe.")
            if i < CYCLES - 1:
                time.sleep(0.6)  # cooldown between cycles


if __name__ == "__main__":
    main()
