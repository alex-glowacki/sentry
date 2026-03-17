#pragma once

#include <stdint.h>

/**
 * @file sentry.h
 * @brief Pin assignments and serial protocol constants for the Sentry firmware.
 */

 // Hardware
 constexpr uint8_t RELAY_PIN = 7;

 // Serial protocol - bytes sent from Raspberry Pi to Arduino
 constexpr char CMD_FIRE = 'F';     // Activate relay
 constexpr char CMD_SAFE = 'S';     // Deactivate relay