#pragma once
/**
 * @file sentry.h
 * @brief Pin assignments, PCA9685 channel mapping, PWM constants, and serial
 *        protocol definitions for the Sentry firmware.
 *
 * Serial protocol (115200 baud, newline-terminated ASCII):
 *  "F\n"       -> activate relay (FIRE)
 *  "S\n"       -> deactivate relay (SAFE)
 *  "P<deg>\n"  -> set pan angle, 0-270 degrees
 *  "T<deg>\n"  -> set tilt angle, 0-180 degrees
 */

#include <stdint.h>

// PCA9685 I2C address (default - A0-A5 all low)
constexpr uint8_t PCA9685_ADDR = 0x40;

// PCA9685 channel assignments
constexpr uint8_t CH_PAN = 0;   // 25 kg servo - pan (0-270 deg)
constexpr uint8_t CH_TILT = 1;  // 25 kg servo - tilt (0-180 deg)
constexpr uint8_t CH_RELAY = 2; // Solenoid relay - FIRE/SAFE

// Servo PWM frequency
constexpr float SERVO_FREQ_HZ = 50.0f; // Standard 50 Hz servo signal

constexpr uint16_t PAN_TICKS_MIN = 102; // 25 kg servo - 0 deg
constexpr uint16_t PAN_TICKS_MAX = 375; // 25 kg servo - 270 deg

constexpr uint16_t TILT_TICKS_MIN = 102; // 25 kg servo - 0 deg (90 deg down)
constexpr uint16_t TILT_TICKS_MAX = 375; // 25 kg servo - 180 deg (90 deg up)

// Relay: full PWM on/off via PCA9685 (channel driven HIGH/LOW)
constexpr uint16_t RELAY_TICKS_ON = 4096; // Special PCA9685 value: always ON
constexpr uint16_t RELAY_TICKS_OFF = 0;   // Special PCA9685 value: always OFF

// Serial protocol command prefixes
constexpr char CMD_FIRE = 'F';
constexpr char CMD_SAFE = 'S';
constexpr char CMD_PAN = 'P';
constexpr char CMD_TILT = 'T';

// Angle limits
constexpr int PAN_DEG_MIN = 0;
constexpr int PAN_DEG_MAX = 180;
constexpr int TILT_DEG_MIN = 0;
constexpr int TILT_DEG_MAX = 180; // +-90 deg from horizontal