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
 
 void setup() {
    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, LOW);   // Start in SAFE state

    Serial.begin(115200);
    while (!Serial) {
        ;   // Wait for USB serial on R4 WiFi
    }

    Serial.println(F("Sentry firmware online."));
 }

 void loop() {
    if (Serial.available() > 0) {
        const char cmd = static_cast<char>(Serial.read());

        switch (cmd) {
            case CMD_FIRE:
            digitalWrite(RELAY_PIN, HIGH);
            Serial.println(F("FIRE"));
            break;

            case CMD_SAFE:
            digitalWrite(RELAY_PIN, LOW);
            Serial.println(F("SAFE"));
            break;

            default:
            Serial.print(F("Unknown command: "));
            Serial.prinln(cmd);
            break;
        }
    }
 }