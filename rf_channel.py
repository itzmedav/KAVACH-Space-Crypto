import math
import random

def calculate_rf_metrics(alt_km: float, freq_mhz: float = 433.0) -> dict:
    """
    Calculates Free-Space Path Loss (FSPL), RSSI, SNR, and Doppler Shift for LEO RF link.
    """
    c = 299792458.0  # Speed of light m/s
    d_m = alt_km * 1000.0
    f_hz = freq_mhz * 1e6
    
    # Free-Space Path Loss (dB)
    fspl_db = 20 * math.log10(d_m) + 20 * math.log10(f_hz) - 147.55
    
    # Link Budget Assumptions (UHF Sub-GHz)
    tx_power_dbm = 10.0  # 10 dBm (10mW CC1101)
    tx_gain_dbi = 2.15   # Monopole
    rx_gain_dbi = 3.0    # Yagi Ground Station
    
    rssi_dbm = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - fspl_db
    noise_floor_dbm = -110.0
    snr_db = rssi_dbm - noise_floor_dbm
    
    # Doppler Shift Simulation (+/- 8 kHz max at 433 MHz in LEO)
    v_rel_ms = 7600.0 * math.sin(alt_km * 0.1)
    doppler_hz = (v_rel_ms / c) * f_hz
    
    return {
        "fspl_db": round(fspl_db, 2),
        "rssi_dbm": round(rssi_dbm, 2),
        "snr_db": round(snr_db, 2),
        "doppler_hz": round(doppler_hz, 1)
    }

def corrupt_payload(payload: bytes) -> bytes:
    """
    Injects single/multi bit-flips into payload bytes to test AES-256-GCM AEAD tamper rejection.
    """
    if not payload:
        return b"\x00"
    
    ba = bytearray(payload)
    target_idx = len(ba) // 2
    ba[target_idx] ^= 0xFF
    
    return bytes(ba)
