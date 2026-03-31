# Sentry

AI-powered airsoft sentry turret. Runs YOLOv8m object detection on a Raspberry Pi 5 with a Hailo AI HAT+ 2, drives pan/tilt servos via a PCA9685, and fires an airsoft motor via a relay — all autonomously.

## Hardware

| Component | Part |
|---|---|
| SBC | Raspberry Pi 5 |
| AI accelerator | Hailo AI HAT+ 2 (HAILO10H) |
| Camera | IMX708 |
| Microcontroller | Arduino Uno R4 WiFi |
| PWM driver | PCA9685 16-channel |
| Pan servo | 25 kg positional, 0–180° |
| Tilt servo | 25 kg positional, 0–180° |
| Firing mechanism | RE-280RA DC motor (airsoft gearbox) via 5V relay |
| Power | LiFePO4 battery + buck converters |

## Wiring

| Arduino Pin | Connected To |
|---|---|
| SDA/SCL | PCA9685 I2C |
| GND | PCA9685 / Relay GND |
| 5V | Relay VCC |

| PCA9685 Channel | Connected To |
|---|---|
| CH0 | Pan servo |
| CH1 | Tilt servo |
| CH2 | Relay signal |

## Software

- **`src/sentry/detector.py`** — Hailo inference, produces `Detection` objects
- **`src/sentry/commander.py`** — Serial interface to Arduino
- **`src/sentry/main.py`** — Targeting loop
- **`src/sentry/preview.py`** — MJPEG preview stream at `http://sentry.local:8080`
- **`firmware/`** — Arduino firmware (PlatformIO)

## Requirements

- Python ≥ 3.11
- HailoRT runtime + `yolov8m_h10.hef` at `/usr/share/hailo-models/`
- PlatformIO (for firmware)

## Installation
```bash
pip install -e ".[dev]"
```

## Usage
```bash
# Basic
sentry --port /dev/ttyACM0

# With preview stream
sentry --port /dev/ttyACM0 --preview

# Verbose with custom burst/cooldown
sentry --port /dev/ttyACM0 --burst-ms 100 --cooldown-ms 600 --verbose
```

### Key options

| Flag | Default | Description |
|---|---|---|
| `--port` | `/dev/ttyACM0` | Arduino serial port |
| `--threshold` | `0.6` | Minimum detection confidence |
| `--targets` | `person` | Comma-separated COCO labels to engage |
| `--burst-ms` | `100` | Motor-on duration per burst |
| `--cooldown-ms` | `600` | Lockout after burst |
| `--pan-range` | `90.0` | Pan half-sweep in degrees |
| `--tilt-range` | `45.0` | Tilt half-sweep in degrees |
| `--pan-dead` | `5.0` | Pan dead-zone in degrees |
| `--tilt-dead` | `5.0` | Tilt dead-zone in degrees |
| `--preview` | off | Enable MJPEG preview stream |

## Firmware
```bash
cd firmware
pio run --target upload
```

Arduino requires a manual double-tap reset to enter the bootloader before flashing.

## Tests
```bash
pytest -v
```

Hardware integration tests (requires connected hardware):
```bash
pytest -v -s -m hardware
```

## Serial Protocol

| Command | Effect |
|---|---|
| `P<deg>\n` | Set pan angle (0–180°) |
| `T<deg>\n` | Set tilt angle (0–180°) |
| `F\n` | Relay ON (fire) |
| `S\n` | Relay OFF (safe) |

Baud rate: 115200.

## License

MIT © 2026 ACG Services, LLC