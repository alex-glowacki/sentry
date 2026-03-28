from sentry.detector import Detection
from sentry.main import _aim


def test_aim_center():
    d = Detection(label="person", confidence=0.9, bbox=(0.25, 0.25, 0.75, 0.75))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 90
    assert tilt == 90


def test_aim_top_right():
    d = Detection(label="person", confidence=0.9, bbox=(0.0, 0.5, 0.5, 1.0))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 135
    assert tilt == 68


def test_aim_full_right():
    d = Detection(label="person", confidence=0.9, bbox=(0.25, 0.75, 0.75, 1.25))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan == 180
    assert tilt == 90


def test_aim_clamped_by_commander():
    d = Detection(label="person", confidence=0.9, bbox=(0.0, 0.9, 0.5, 1.0))
    pan, tilt = _aim(d, pan_range=90.0, tilt_range=45.0)
    assert pan > 90
