from sentry.main import _aim
from sentry.detector import Detection


def test_aim_center():
    d = Detection(label="person", confidence=0.9, bbox=(0.25, 0.25, 0.75, 0.75))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 180
    assert tilt == 90


def test_aim_top_right():
    # Box centred at (x=0.75, y=0.25) — top-right quadrant
    d = Detection(label="person", confidence=0.9, bbox=(0.0, 0.5, 0.5, 1.0))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 225  # cx=0.5 → 180 + 0.5*90
    assert tilt == 68  # cy=-0.5 → 90 + (-0.5)*45 = 67.5 → rounds to 6


def test_aim_full_right():
    # Box centred at right edge (x_centre = 1.0)
    d = Detection(label="person", confidence=0.9, bbox=(0.25, 0.75, 0.75, 1.25))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 270
    assert tilt == 90


def test_aim_clamped_by_commander():
    # _am itself doesn't clamp - Commander.pan/tilt do
    d = Detection(label="person", confidence=0.9, bbox=(0.0, 0.9, 0.5, 1.0))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan > 180
