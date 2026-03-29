"""preview.py - MJPEG HTTP preview streamer for the Sentry targeting loop.

Serves an annotated live feed for HTTP on a background thread.
Access at http://sentry.local:8080 (or the Pi's IP) in any browser.
"""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_BOUNDARY = b"frame"


class PreviewStreamer:
    """Annotates frames and serves them as an MJPEG stream over HTTP.

    Args:
        port: TCP port to serve on (default 8080).
        frame_size: Expected frame dimensions as (width, height).
    """

    def __init__(self, port: int = 8080, frame_size: tuple[int, int] = (640, 640)) -> None:
        self._port = port
        self._frame_size = frame_size
        self._lock = threading.Lock()
        self._jpeg: bytes = b""
        self._server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the HTTP server on a background thread."""
        streamer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass  # suppress per-request access logs

            def do_GET(self) -> None:
                if self.path != "/":
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    f"multipart/x-mixed-replace; boundary={_BOUNDARY.decode()}",
                )
                self.end_headers()
                try:
                    while True:
                        with streamer._lock:
                            jpeg = streamer._jpeg
                        if jpeg:
                            self.wfile.write(
                                b"--" + _BOUNDARY + b"\r\n"
                                b"Content-Type: image/jpeg\r\n"
                                b"Content-Length: " + str(len(jpeg)).encode() + b"\r\n"
                                b"\r\n" + jpeg + b"\r\n"
                            )
                except (BrokenPipeError, ConnectionResetError):
                    pass

        self._server = HTTPServer(("", self._port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        logger.info("Preview stream available at http://sentry.local:%d", self._port)

    def stop(self) -> None:
        """Shut down the HTTP server."""
        if self._server is not None:
            self._server.shutdown()
            self._server = None

    def push(
        self,
        frame: np.ndarray[Any, np.dtype[np.uint8]],
        detections: list[Any],
        engaged: list[Any],
        pan_deg: int | None,
        tilt_deg: int | None,
        last_pan: int,
        last_tilt: int,
        pan_dead: float,
        tilt_dead: float,
        pan_range: float,
        tilt_range: float,
    ) -> None:
        """Annotate *frame* and push it to the stream.

        Args:
            frame: RAW RGB888 frame from picamera2.
            detections: All detections from the current frame.
            engaged: Subset of detections matching the target list.
            pan_deg: Computed pan angle for the best target, or None.
            tilt_deg: Computed tilt angle for the best target, or None.
            last_pan: Last commanded pan angle (for dead zone overlay).
            last_tilt: Last commanded tilt angle (for dead zone overlay).
            pan_dead: Pan dead zone half-width in degrees.
            tilt_dead: Tilt dead zone half-width in degrees.
            pan_range: Pan half-sweep in degrees (maps frame edge → ±pan_range).
            tilt_range: Tilt half-sweep in degrees.
        """
        # OpenCV expects BGR
        annotated = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        h, w = annotated.shape[:2]

        # --- All detections (gray) ---
        for det in detections:
            y1, x1, y2, x2 = det.bbox
            p1 = (int(x1 * w), int(y1 * h))
            p2 = (int(x2 * w), int(y2 * h))
            cv2.rectangle(annotated, p1, p2, (120, 120, 120), 1)
            cv2.putText(
                annotated,
                f"{det.label} {det.confidence:.2f}",
                (p1[0], max(p1[1] - 6, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (120, 120, 120),
                1,
            )

        # -- Engaged detections (green) ---
        for det in engaged:
            y1, x1, y2, x2 = det.bbox
            p1 = (int(x1 * w), int(y1 * h))
            p2 = (int(x2 * w), int(y2 * h))
            cv2.rectangle(annotated, p1, p2, (0, 220, 0), 2)
            cv2.putText(
                annotated,
                f"{det.label} {det.confidence:.2f}",
                (p1[0], max(p1[1] - 6, 12)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 220, 0),
                1,
            )

        # --- Dead zone indicator (blue circle at last commanded position) ---
        # Convert last servo angles back to pixel coordinates
        lx = int((((last_pan - 90) / pan_range) + 1.0) / 2.0 * w)
        ly = int((((last_tilt - 90) / tilt_range) + 1.0) / 2.0 * h)
        dz_rx = int(pan_dead / pan_range * w / 2)
        dz_ry = int(tilt_dead / tilt_range * h / 2)
        cv2.ellipse(annotated, (lx, ly), (dz_rx, dz_ry), 0, 0, 360, (255, 100, 0), 1)

        # --- Crosshair at aimed pixel (red) ---
        if pan_deg is not None and tilt_deg is not None:
            ax = int((((pan_deg - 90) / pan_range) + 1.0) / 2.0 * w)
            ay = int((((tilt_deg - 90) / tilt_range) + 1.0) / 2.0 * h)
            size = 12
            cv2.line(annotated, (ax - size, ay), (ax + size, ay), (0, 0, 255), 2)
            cv2.line(annotated, (ax, ay - size), (ax, ay + size), (0, 0, 255), 2)
            cv2.circle(annotated, (ax, ay), size, (0, 0, 255), 1)

        _, jpeg = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 70])
        with self._lock:
            self._jpeg = jpeg.tobytes()
