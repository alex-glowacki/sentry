# Sentry — Architecture

## Overview

```
[Camera] ──► [Pi 5 + Hailo AI HAT+ 2] ──── USB Serial ────► [Arduino Uno R4 WiFi] ──► [Relay] ──► [Airsoft]
```

## Separation of Concerns

| Component      | Responsibility                                        |
| -------------- | ----------------------------------------------------- |
| `detector.py`  | Hailo inference — produces `Detection` objects        |
| `commander.py` | Serial interface — translates decisions into commands |
| `main.py`      | Targeting loop — ties detector and commander together |
| `firmware/`    | Arduino — receives bytes, drives hardware only        |

## Serial Protocol

| Byte | Direction    | Effect            |
| ---- | ------------ | ----------------- |
| `T<deg>`  | Pi → Arduino | Set tilt angle, 0-180 degrees  |
| `P<deg>`  | Pi → Arduino | Set pan angle, 0-180 degrees   |
| `F`       | Pi → Arduino | Relay HIGH (FIRE)              |
| `S`       | Pi → Arduino | Relay LOW (SAFE)               |

Baud rate: `115200`. Connection managed as a context manager in `Commander`.

## Wiring

| Arduino Pin | Connected To       |
| ----------- | ------------------ |
| `7`         | Relay signal input |
| `GND`       | Relay GND          |
| `5V`        | Relay VCC          |
