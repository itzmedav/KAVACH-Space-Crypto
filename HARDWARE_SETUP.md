# KAVACH Hardware-in-the-Loop Setup & BOM Guide

This document details the physical hardware configuration for running KAVACH over actual 433 MHz Sub-GHz RF links between an ESP32-S3 Ground Station and an ESP32-S3 Spacecraft.

---

## 🛍️ Bill of Materials (Total Budget: ~₹1,800 – ₹2,200)

| Item | Qty | Target Vendor | Approx Price (INR) |
|---|---|---|---|
| **ESP32-S3 DevKit N8R8** (Dual Type-C, PSRAM) | 2 | Robu.in / Orange | ₹1,100 (₹550 each) |
| **CC1101 433 MHz RF Transceiver Module** | 2 | Robu.in / Amazon India | ₹500 (₹250 each) |
| **SMA 433 MHz High-Gain Antennas** | 2 | Robu.in | ₹200 (₹100 each) |
| **Breadboards & Jumper Wires** | 1 Set | Robu.in / Local | ₹100 |

---

## 🔌 SPI Pinout Mapping (ESP32-S3 -> CC1101 Module)

Connect both the **Spacecraft ESP32-S3** and **Ground Station ESP32-S3** to their respective CC1101 modules according to this SPI layout:

| CC1101 Pin | ESP32-S3 GPIO | Function | Wire Color |
|---|---|---|---|
| **VCC** | 3.3V | Power (Do NOT use 5V!) | Red |
| **GND** | GND | Ground | Black |
| **CSN / CS** | GPIO 10 | SPI Chip Select | Yellow |
| **SCK** | GPIO 12 | SPI Clock | Green |
| **MOSI** | GPIO 9 | SPI Master Out Slave In | Blue |
| **MISO** | GPIO 11 | SPI Master In Slave Out | White |
| **GDO0** | GPIO 14 | Packet Received Interrupt | Orange |
| **GDO2** | GPIO 13 | Packet Sent Interrupt | Purple |

---

## ⚡ Flashing via VS Code + PlatformIO

1. Install **VS Code** + **PlatformIO Extension**.
2. Open `C:\Users\david\KAVACH` in VS Code.
3. Plug in the Spacecraft ESP32-S3 via USB.
4. Run task: `PlatformIO: Upload (kavach_satellite)`.
5. Open Serial Monitor at **115200 baud** to view real-time flight logs.
