# KAVACH Hardware-in-the-Loop Pre-Flight Checklist

This checklist guides you through flashing the ESP32-S3 microcontroller hardware twin for KAVACH over CC1101 Sub-GHz RF links.

---

## 📋 Phase 1: Software & IDE Preparation

- [x] Install VS Code (Visual Studio Code x64).
- [x] Install PlatformIO Extension:
  1. Open VS Code.
  2. Go to Extensions (Ctrl+Shift+X).
  3. Search PlatformIO IDE and click Install.
  4. Restart VS Code once installation completes.

---

## 🛍️ Phase 2: Hardware Acquisition (Robu.in Allocation)

| Component | Quantity | Purpose | Checked |
|---|---|---|---|
| ESP32-S3 DevKit N8R8 | 2 | Spacecraft & Ground Station Microcontrollers | [ ] |
| CC1101 433 MHz SPI Module | 2 | Sub-GHz RF Transceiver Hardware | [ ] |
| SMA 433 MHz Antennas | 2 | RF Link High-Gain Transmit/Receive | [ ] |
| Breadboard + Jumper Wires | 1 Set | SPI Pin Wiring | [ ] |

---

## 🔌 Phase 3: Wiring Protocol Verification

Connect ESP32-S3 to CC1101 according to this pinout table:

  ESP32-S3 (GPIO 10) ---> CC1101 CSN
  ESP32-S3 (GPIO 12) ---> CC1101 SCK
  ESP32-S3 (GPIO 9)  ---> CC1101 MOSI
  ESP32-S3 (GPIO 11) ---> CC1101 MISO
  ESP32-S3 (GPIO 14) ---> CC1101 GDO0
  ESP32-S3 (GPIO 13) ---> CC1101 GDO2
  ESP32-S3 (3.3V)    ---> CC1101 VCC (DO NOT USE 5V!)
  ESP32-S3 (GND)     ---> CC1101 GND

---

## ⚡ Phase 4: Flashing Procedure

1. Spacecraft Board (Node 1):
   - Connect Spacecraft ESP32-S3 via USB-C to PC.
   - Open VS Code at C:\Users\david\KAVACH.
   - Open PlatformIO tab -> Select env:kavach_satellite -> Click Upload & Monitor.
   - Confirm Serial Monitor output at 115200 baud:
     [RF] CC1101 Transceiver Initialized at 433 MHz GFSK.

2. Ground Station Board (Node 2):
   - Connect Ground Station ESP32-S3 via second USB-C port.
   - Open PlatformIO tab -> Select env:kavach_ground -> Click Upload & Monitor.
   - Confirm Serial Monitor output:
     [RF TX] Transmitting CCSDS TC Frame: APID 0x200.

3. Verify Spacecraft Acceptance:
   - Spacecraft Serial Monitor should report:
     [RF RX] CCSDS Frame Received: APID 0x200 | Seq 1 | RSSI -42.0 dBm
     [SUCCESS] Packet Authenticated & Enqueued for Actuation.
