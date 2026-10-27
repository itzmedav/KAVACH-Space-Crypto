import math
import numpy as np

def calculate_rf_metrics(alt_km: float = 500.0, freq_mhz: float = 433.92, rel_velocity_kms: float = 7.5):
    """
    Calculates LEO Space-to-Ground and Inter-Satellite Link (ISL) RF Physics metrics:
    - Free Space Path Loss (FSPL) in dB
    - Doppler Frequency Shift (kHz)
    - Atmospheric & Ionospheric Attenuation (dB)
    - Rician & Rayleigh Fading Model (dB)
    - Bit Error Rate (BER) for BPSK/QPSK modulation
    """
    c = 299792458.0  # Speed of light m/s
    freq_hz = freq_mhz * 1e6
    distance_m = alt_km * 1000.0
    
    # Free Space Path Loss (FSPL)
    fspl_db = 20 * math.log10(distance_m) + 20 * math.log10(freq_hz) - 147.55
    
    # Orbital Doppler Shift
    v_m_s = rel_velocity_kms * 1000.0
    doppler_shift_hz = freq_hz * (v_m_s / c)
    doppler_shift_khz = doppler_shift_hz / 1000.0
    
    # Atmospheric Absorption
    atmos_loss_db = 0.35 + 0.15 * math.sin(math.radians(35.0))
    
    # Rician Fading Channel
    k_factor_db = 6.0
    k_linear = 10 ** (k_factor_db / 10.0)
    rician_fading_std = math.sqrt(1.0 / (2.0 * (k_linear + 1.0)))
    rician_fading_loss_db = abs(float(np.random.normal(0, rician_fading_std)))
    
    # Received Power
    tx_power_dbm = 30.0
    tx_gain_dbi = 2.15
    rx_gain_dbi = 5.0
    rx_power_dbm = tx_power_dbm + tx_gain_dbi + rx_gain_dbi - fspl_db - atmos_loss_db - rician_fading_loss_db
    
    # Thermal Noise Floor & SNR
    bw_hz = 125000.0
    thermal_noise_dbm = -174.0 + 10 * math.log10(bw_hz) + 4.0
    snr_db = rx_power_dbm - thermal_noise_dbm
    
    # Bit Error Rate (BER)
    snr_linear = 10 ** (snr_db / 10.0)
    eb_n0_linear = snr_linear * (bw_hz / 9600.0)
    ber = 0.5 * math.erfc(math.sqrt(max(0.0, eb_n0_linear)))
    
    return {
        "alt_km": alt_km,
        "freq_mhz": freq_mhz,
        "fspl_db": round(fspl_db, 2),
        "doppler_khz": round(doppler_shift_khz, 3),
        "atmos_loss_db": round(atmos_loss_db, 2),
        "fading_loss_db": round(rician_fading_loss_db, 2),
        "rx_power_dbm": round(rx_power_dbm, 2),
        "snr_db": round(snr_db, 2),
        "ber": ber,
        "link_margin_db": round(snr_db - 10.0, 2)
    }

if __name__ == '__main__':
    print("Space RF Metrics:", calculate_rf_metrics())
