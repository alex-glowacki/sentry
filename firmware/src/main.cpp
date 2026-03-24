/**
 * @file main.cpp
 * @brief Sentry firmware - receives newline-terminated ASCII commands over USB
 *        serial and drives pan/tilt servos + solenoid relay via PCA9685.
 *
 * Serial protocol (115200 baud):
 *  "F\n"         -> activate relay (FIRE)
 *  "S\n"         -> deactivate relay (SAFE)
 *  "P<deg>\n"    -> set pan angle, 0-359 degrees
 *  "T<deg>\n"    -> set tilt angle, 0-180 degrees
 */

#include "sentry.h"
#include <Adafruit_PWMServoDriver.h>
#include <Arduino.h>
#include <Wire.h>

// Globals
static Adafruit_PWMServoDriver pca = Adafruit_PWMServoDriver(PCA9685_ADDR);
static String serialBuf;

// Helpers
/**
 * Map an integer value from one range to another.
 * Mirrors Arduino map() but operates on long to avoid overflow.
 */
static long mapRange(long x, long inMin, long inMax, long outMin, long outMax) {
  return (x - inMin) * (outMax - outMin) / (inMax - inMin) + outMin;
}

/**
 * Drive the pan servo to the requested speed tick directly.
 * For 360-deg continuous servo: PAN_TICKS_MID = stop,
 * below = one direction, above = other direction.
 */
static void setPan(uint16_t ticks) {
  ticks = constrain(ticks, PAN_TICKS_MIN, PAN_TICKS_MAX);
  pca.setPWM(CH_PAN, 0, ticks);
}

/**
 * Drive the tilt servo to the requested angle (0-180 deg).
 * Clamps input to valid range before writing.
 */
static void setTilt(int degrees) {
  degrees = constrain(degrees, TILT_DEG_MIN, TILT_DEG_MAX);
  const uint16_t ticks = static_cast<uint16_t>(mapRange(
      degrees, TILT_DEG_MIN, TILT_DEG_MAX, TILT_TICKS_MIN, TILT_TICKS_MAX));
  pca.setPWM(CH_TILT, 0, ticks);
}

/**
 * Engage or release the solenoid relay.
 * Uses PCA9685 full-on/off rather than PWM to avoid relay chatter.
 */
static void setRelay(bool on) {
  if (on) {
    pca.setPin(CH_RELAY, RELAY_TICKS_ON);
  } else {
    pca.setPin(CH_RELAY, RELAY_TICKS_OFF);
  }
}

/**
 * Parse and dispatch a complete comand string (no trailing newline).
 * Responds over Serial for acknowledgement / debugging.
 */
static void dispatchCommand(const String &cmd) {
  if (cmd.length() == 0)
    return;

  const char prefix = cmd.charAt(0);

  switch (prefix) {
  case CMD_FIRE:
    setRelay(true);
    Serial.println(F("FIRE"));
    break;

  case CMD_SAFE:
    setRelay(false);
    Serial.println(F("SAFE"));
    break;

  case CMD_PAN: {
    const int deg = cmd.substring(1).toInt();
    // Map degree command to ticks for caller convenience,
    // but pan is continuous - deg is treated as a speed/position hint.
    // 180 deg -> MID (stop), 0 -> MIN, 359 -> MAX.
    const uint16_t ticks = static_cast<uint16_t>(
        mapRange(deg, PAN_DEG_MIN, PAN_DEG_MAX, PAN_TICKS_MIN, PAN_TICKS_MAX));
    setPan(ticks);
    Serial.print(F("PAN "));
    Serial.println(deg);
    break;
  }

  case CMD_TILT: {
    const int deg = cmd.substring(1).toInt();
    setTilt(deg);
    Serial.print(F("TILT "));
    Serial.println(deg);
    break;
  }

  default:
    Serial.print(F("Unknown command: "));
    Serial.println(cmd);
    break;
  }
}

// Arduino lifecycle
void setup() {
  Serial.begin(115200);
  while (!Serial) {
    ; // Wait for USB serial on R4 WiFi
  }

  Wire.begin();
  pca.begin();
  pca.setOscillatorFrequency(27000000);
  pca.setPWMFreq(SERVO_FREQ_HZ);
  delay(10); // Allow PCA9685 to stabilize after freq change

  // Safe relay immediately after PCA9685 is initialized
  setRelay(false);

  // Stop continuous pan servo at mid-point
  pca.setPWM(CH_PAN, 0, PAN_TICKS_MID);

  // Center tilt servo
  setTilt(90);

  serialBuf.reserve(16);

  Serial.println(F("Sentry firmware online."));
}

void loop() {
  while (Serial.available() > 0) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\n') {
      serialBuf.trim();
      dispatchCommand(serialBuf);
      serialBuf = "";
    } else {
      serialBuf += c;
    }
  }
}