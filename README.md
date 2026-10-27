# 🛡️ KAVACH — Post-Quantum Space Communication Protocol

> **A native implementation of NIST FIPS 203 (ML-KEM-768) post-quantum cryptography with AES-256-GCM AEAD payload encryption for LEO satellite command & telemetry links.**

---

## 📌 Executive Summary

Modern satellite communication links rely heavily on classical asymmetric algorithms like **RSA-2048** and **ECDH-P256** for key exchange. With the rapid advancement of quantum computing, algorithms like **Shor’s Algorithm** will render these cryptographic mechanisms obsolete within the next 10–15 years. Furthermore, adversaries are currently conducting **"Harvest Now, Decrypt Later"** attacks—capturing encrypted satellite telemetry today to decrypt retroactively once quantum processors become available.

**KAVACH** is a lightweight, zero-trust, post-quantum cryptographic space communication framework designed to solve this gap for small satellites (CubeSats) and deep-space missions.

---

## 🚀 Key Features

* **Quantum-Resistant Key Exchange:** Native C++ integration of **ML-KEM-768** (NIST FIPS 203 / Kyber-768) operating over Module-Lattice Learning With Errors (Module-LWE).
* **Authenticated Payload Encryption:** Symmetric data transport utilizing **AES-256-GCM** (Galois/Counter Mode) with strict 96-bit nonce tracking.
* **Low-Latency Architecture:** Key generation latency of **~0.17 ms**, enabling rapid key rotation without starving spacecraft CPU resources.
* **Zero-Trust Command Verification:** Rejects unencrypted, tampered, or spoofed commands automatically.
* **Real-Time Mission Control GUI:** Streamlit & Plotly dark-mode ground station dashboard displaying live decrypted telemetry feeds.
* **Attack Surface Testing:** Built-in simulations for eavesdropping, command spoofing, and replay-attack resistance.

---

## 🏗️ System Architecture

```text
+----------------------------------+      UHF / TCP Link       +----------------------------------+
|         GROUND STATION           | <=======================> |           SATELLITE             |
|   (Mission Control Dashboard)    |   ML-KEM-768 + AES-256    |  (Spacecraft Flight Software)   |
+----------------------------------+                           +----------------------------------+
| - Generates Ephemeral Keypair    |                           | - Generates ML-KEM-768 Public Key|
| - Encapsulates Shared Secret     | ===== Encapsulated CT ==> | - Decapsulates Shared Secret    |
| - Transmits Encrypted Commands   | <===== Encrypted TLM ==== | - Processes & Encrypts Payload  |
+----------------------------------+                           +----------------------------------+
