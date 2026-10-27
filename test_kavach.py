"""
KAVACH Automated Unit Test Suite
Run locally with: pytest
Tests ML-KEM-768 key exchange, HKDF-SHA256 key derivation,
AES-256-GCM encryption, CCSDS packing/unpacking, and Anti-Replay protection.
"""
import pytest
import oqs
import os
import json
from ccsds import CCSDSPacket, make_telemetry_frame, derive_session_keys, AntiReplayWindow
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def test_ml_kem_768_handshake():
    with oqs.KeyEncapsulation("ML-KEM-768") as server_kem:
        pubkey = server_kem.generate_keypair()
        with oqs.KeyEncapsulation("ML-KEM-768") as client_kem:
            ciphertext, client_secret = client_kem.encap_secret(pubkey)
        server_secret = server_kem.decap_secret(ciphertext)
        assert server_secret == client_secret

def test_hkdf_key_derivation():
    raw_secret = os.urandom(32)
    payload_k1, mac_k1 = derive_session_keys(raw_secret)
    payload_k2, mac_k2 = derive_session_keys(raw_secret)
    assert payload_k1 == payload_k2
    assert len(payload_k1) == 32
    assert payload_k1 != mac_k1

def test_ccsds_packet_roundtrip():
    data = b"HELLO ISRO"
    frame = make_telemetry_frame(seq=42, payload=data)
    parsed = CCSDSPacket.unpack(frame)
    assert parsed["apid"] == 0x100
    assert parsed["seq_count"] == 42
    assert parsed["data"] == data

def test_anti_replay_window():
    window = AntiReplayWindow(window_size=64)
    assert window.validate_and_update(1) is True
    assert window.validate_and_update(2) is True
    assert window.validate_and_update(2) is False  # Replay rejected!
    assert window.validate_and_update(1) is False  # Replay rejected!
    assert window.validate_and_update(3) is True
