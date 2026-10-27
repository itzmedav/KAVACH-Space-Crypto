import pytest
from ccsds import MLKEM768Simulator, HKDFKeyDerivation, AES256GCMCipher, CCSDSHelper, SlidingWindowAntiReplay
from rf_channel import calculate_rf_metrics
from constellation import ConstellationManager

def test_ml_kem_768_handshake():
    sim = MLKEM768Simulator()
    pk, sk = sim.generate_keypair()
    ciphertext, sender_secret = sim.encapsulate(pk)
    receiver_secret = sim.decapsulate(ciphertext, sk)
    assert sender_secret == receiver_secret
    assert len(pk) == 1184
    assert len(ciphertext) == 1088

def test_hkdf_key_derivation():
    shared_secret = b"QUANTUM_SECRET_SEED_12345"
    key1 = HKDFKeyDerivation.derive_key(shared_secret)
    key2 = HKDFKeyDerivation.derive_key(shared_secret)
    assert key1 == key2
    assert len(key1) == 32

def test_ccsds_packet_roundtrip():
    header = CCSDSHelper.pack_primary_header(apid=0x100, seq_count=42, data_len=64)
    parsed = CCSDSHelper.unpack_primary_header(header)
    assert parsed["apid"] == 0x100
    assert parsed["seq_count"] == 42
    assert parsed["data_len"] == 64

def test_anti_replay_window():
    filter = SlidingWindowAntiReplay(window_size=64)
    assert filter.check_and_update(1) == True
    assert filter.check_and_update(2) == True
    assert filter.check_and_update(1) == False
    assert filter.check_and_update(5) == True
    assert filter.check_and_update(3) == True

def test_constellation_isl_handshake():
    cm = ConstellationManager()
    cm.update_orbit_positions()
    res = cm.establish_isl_handshake()
    assert res["handshake_status"] == "SUCCESS"
    ranges = cm.calculate_isl_ranges()
    assert ranges["Alpha-Beta_km"] > 0

def test_rf_channel_physics():
    metrics = calculate_rf_metrics(alt_km=500.0, freq_mhz=433.92)
    assert metrics["fspl_db"] > 130.0
    assert metrics["doppler_khz"] > 5.0
    assert metrics["snr_db"] > 0.0
