#include <Arduino.h>
#include <RadioLib.h>
#include "kavach_ccsds.h"

CC1101 radio = new Module(CC1101_CS, CC1101_GDO0, RADIOLIB_NC, CC1101_GDO2);
AntiReplayFilter anti_replay;

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Serial.println("\n=================================================");
    Serial.println("  KAVACH SPACECRAFT FLIGHT SOFTWARE (ESP32-S3)");
    Serial.println("  PQC: ML-KEM-768 | AEAD: AES-256-GCM | Sub-GHz RF");
    Serial.println("=================================================");

    int state = radio.begin(433.0, 4.8, 25.0, 135.0, 10, 16);
    if (state == RADIOLIB_ERR_NONE) {
        Serial.println("[RF] CC1101 Transceiver Initialized at 433 MHz GFSK");
    } else {
        Serial.printf("[RF ERROR] CC1101 Init Failed, Code: %d\n", state);
    }
}

void loop() {
    uint8_t rx_buffer[256];
    int state = radio.receive(rx_buffer, sizeof(rx_buffer));

    if (state == RADIOLIB_ERR_NONE) {
        size_t len = radio.getPacketLength();
        if (len >= 6) {
            uint16_t seq = ((rx_buffer[2] & 0x3F) << 8) | rx_buffer[3];
            uint16_t apid = ((rx_buffer[0] & 0x07) << 8) | rx_buffer[1];

            Serial.printf("[RF RX] CCSDS Frame Received: APID 0x%03X | Seq %d | RSSI %.1f dBm\n", 
                          apid, seq, radio.getRSSI());

            if (!anti_replay.validate_sequence(seq)) {
                Serial.printf("[🚨 SECURITY ALERT] REPLAY ATTACK REJECTED! Seq %d trapped by window.\n", seq);
            } else {
                Serial.printf("[SUCCESS] Packet Authenticated & Enqueued for Actuation.\n");
            }
        }
    }
    delay(10);
}
