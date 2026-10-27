#include <Arduino.h>
#include <RadioLib.h>
#include "kavach_ccsds.h"

CC1101 radio = new Module(CC1101_CS, CC1101_GDO0, RADIOLIB_NC, CC1101_GDO2);
uint16_t ground_seq = 1;

void setup() {
    Serial.begin(115200);
    while (!Serial && millis() < 3000);

    Serial.println("\n=================================================");
    Serial.println("  KAVACH GROUND STATION TRANSMITTER (ESP32-S3)");
    Serial.println("  CCSDS Telecommand Engine | Sub-GHz RF TX Mode");
    Serial.println("=================================================");

    int state = radio.begin(433.0, 4.8, 25.0, 135.0, 10, 16);
    if (state == RADIOLIB_ERR_NONE) {
        Serial.println("[RF] CC1101 Transceiver Ready at 433 MHz GFSK");
    } else {
        Serial.printf("[RF ERROR] CC1101 Init Failed, Code: %d\n", state);
    }
}

void loop() {
    uint8_t tx_packet[64];
    
    // Pack CCSDS 133.0-B Primary Header for APID 0x200 (Telecommand)
    pack_ccsds_primary(tx_packet, APID_COMMAND, 1, ground_seq, 24);
    
    // Payload mock
    snprintf((char*)(tx_packet + 6), 18, "TC_CMD_SET_MODE");

    Serial.printf("[RF TX] Transmitting CCSDS TC Frame: APID 0x200 | Seq %d ... ", ground_seq);
    int state = radio.transmit(tx_packet, 24);

    if (state == RADIOLIB_ERR_NONE) {
        Serial.println("SENT OK!");
    } else {
        Serial.printf("FAILED (Error %d)\n", state);
    }

    ground_seq++;
    delay(3000); // Send telecommand frame every 3 seconds
}
