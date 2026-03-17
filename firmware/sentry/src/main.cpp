/**
 * @file main.cpp
 * @brief Sentry firmware - receives single-byte commands over USB serial
 *        and drives a relay to fire an airsoft mechanism.
 * 
 * Serial protocol (115200 baud):
 *    'F' -> activate relay (FIRE)
 *    'S' -> deactivate relay (SAFE)
 */

 #include <Arduino.h>
 #include "sentry.h"
 