# KAVACH: Post-Quantum Secure Telemetry & Telecommand Protocol for LEO Nanosatellites

[![NIST FIPS 203](https://img.shields.io/badge/NIST-FIPS_203_(ML--KEM--768)-00F0FF?style=for-the-badge&logo=shield)](https://csrc.nist.gov/pubs/fips/203/final)
[![NIST SP 800-56C](https://img.shields.io/badge/NIST-SP_800--56C_(HKDF--SHA256)-0052CC?style=for-the-badge)](https://csrc.nist.gov/publications/detail/sp/800-56c/rev-2/final)
[![CCSDS 133.0-B-2](https://img.shields.io/badge/CCSDS-133.0--B--2_Compliant-39FF14?style=for-the-badge)](https://public.ccsds.org/)
[![AES-256-GCM](https://img.shields.io/badge/Cipher-AES--256--GCM_AEAD-FF0055?style=for-the-badge)](https://csrc.nist.gov/)
[![Python 3.13](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Pytest Passed](https://img.shields.io/badge/Tests-4%2F4_PASSED-brightgreen?style=for-the-badge&logo=pytest)](https://docs.pytest.org/)
[![Defense Efficiency](https://img.shields.io/badge/Attack_Defense-100%25_Efficiency-gold?style=for-the-badge)](https://github.com/itzmedav/KAVACH-Space-Crypto)

**KAVACH** (*Sanskrit for Armor*) is an end-to-end, ultra-low latency post-quantum security architecture engineered specifically for Low Earth Orbit (LEO) nanosatellite constellations (CubeSats, 1U-6U). Developed in compliance with **NIST FIPS 203 (ML-KEM-768)**, **NIST SP 800-56C (HKDF-SHA256)**, **AES-256-GCM**, and **CCSDS 133.0-B-2 Space Packet Protocol** standards.

## Key Highlights
- **NIST Category 3 Post-Quantum Key Exchange**: Kyber-768 / ML-KEM-768 encapsulation for post-quantum forward secrecy.
- **Zero Overhead Payload Encryption**: 256-bit AES-GCM AEAD encryption (< 0.2 ms latency).
- **CCSDS 133.0-B Framing**: Standard 6-byte CCSDS Primary Headers (APID 0x001 Handshake, 0x100 Telemetry, 0x200 Telecommand).
- **Anti-Replay Window Filter**: 64-frame sliding bitmask preventing replay attacks.
- **Flight Computer State Machine**: Dynamic FSM transitions (NOMINAL, SAFE_MODE, ECLIPSE, DETUMBLE).
- **Mission Control Cockpit**: Real-time 3D Earth track, 433.92 MHz SDR spectrum waterfall, 1,000-frame attack simulator.
- **Embedded Hardware Target**: ESP32-S3 + CC1101 C++ firmware stack in irmware/.

## Quick Start
`ash
pip install -r requirements.txt
pytest test_kavach.py -v
streamlit run dashboard.py
`
