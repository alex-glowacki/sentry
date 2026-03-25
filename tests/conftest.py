"""Pytest configuration - mock Pi-only dependencies for CI."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# hailo_platform and picamera2 are only available on the Pi.
# Mock them before any test module imports sentry.detector or sentry.main.
for _mod in ("hailo_platform", "picamera2"):
    sys.modules[_mod] = MagicMock()
