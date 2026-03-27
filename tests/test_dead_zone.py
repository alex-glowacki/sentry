"""Tests for the _in_dead_zone helper."""

from __future__ import annotations

import pytest

from sentry.main import _in_dead_zone

_PAN_DEAD = 5.0
_TILT_DEAD = 5.0


@pytest.mark.parametrize(
    ("pan_deg", "tilt_deg", "last_pan", "last_tilt", "expected"),
    [
        # Exactly at last position — suppress
        (180, 90, 180, 90, True),
        # Both axes within threshold — suppress
        (183, 93, 180, 90, True),
        # Exactly on threshold boundary — suppress (<=)
        (185, 95, 180, 90, True),
        # Pan just outside threshold — move
        (186, 90, 180, 90, False),
        # Tilt just outside threshold — move
        (180, 96, 180, 90, False),
        # Both axes outside threshold — move
        (190, 100, 180, 90, False),
        # Pan inside, tilt outside — move (AND logic)
        (182, 96, 180, 90, False),
        # Negative delta (target moved left/down) — suppress
        (177, 87, 180, 90, True),
        # Negative delta outside threshold — move
        (174, 90, 180, 90, False),
    ],
)
def test_in_dead_zone(
    pan_deg: int,
    tilt_deg: int,
    last_pan: int,
    last_tilt: int,
    expected: bool,
) -> None:
    assert _in_dead_zone(pan_deg, tilt_deg, last_pan, last_tilt, _PAN_DEAD, _TILT_DEAD) is expected


def test_zero_dead_zone_never_suppresses() -> None:
    """Dead-zone of 0 should only suppress when position is exactly unchanged."""
    assert _in_dead_zone(181, 90, 180, 90, 0.0, 0.0) is False
    assert _in_dead_zone(180, 90, 180, 90, 0.0, 0.0) is True


def test_asymetric_thresholds() -> None:
    """Pan and tilt dead-zones are independent."""
    # Pan threshold=10, tilt threshold=2
    assert _in_dead_zone(188, 91, 180, 90, 10.0, 2.0) is True  # both inside
    assert _in_dead_zone(188, 93, 180, 90, 10.0, 2.0) is False  # tilt outside
    assert _in_dead_zone(191, 91, 180, 90, 10.0, 2.0) is False  # pan outside
