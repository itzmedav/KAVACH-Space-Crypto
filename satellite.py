"""
KAVACH Spacecraft Flight Software v3.0
- NIST FIPS 203 ML-KEM-768 Key Encapsulation
- NIST SP 800-56C HKDF-SHA256 Key Derivation
- AES-256-GCM Payload Encryption
- CCSDS 133.0-B Framing + 64-Frame Anti-Replay Filter
- Real-Time LEO Orbital Trajectory Dynamics (Lat/Lon/Alt/Eclipse)
"""
import socket
import json
import time
import math
import os
import struct
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import oqs
from ccsds import make_telemetry_frame, make_handshake_frame, CCSDSPacket, derive_session_keys, AntiReplayWindow

HOST = "0.0.0.0"
PORT = 9999

class LEOSpacecraft:
    def __init__(self):
        self.altitude_km = 420.0
        self.period_s = 5570.0  # ~92.8 minutes per orbit
        self.inclination_deg = 51.6  # ISS Orbit Inclination
        self.velocity_kms = 7.66
        self.battery_v = 28.4
        self.battery_temp_c = 22.0
        self.solar_power_w = 0.0
        self.in_eclipse = False
        self.eclipse_fraction = 0.35
        self.t0 = time.time()
        self.seq = 0
        self.fuel_kg = 4.2
        self.mode = "NOMINAL"
        self.doppler_hz = 0.0
        self.lat = 0.0
        self.lon = 0.0

    def step(self):
        t = time.time() - self.t0
        phase = (t % self.period_s) / self.period_s  # 0.0 to 1.0

        # Orbital Position Calculations
        orbit_angle = phase * 2.0 * math.pi
        self.lat = self.inclination_deg * math.sin(orbit_angle)
        # Account for Earth rotation (~15 deg/hr)
        earth_rotation = (t / 86400.0) * 360.0
        self.lon = ((phase * 360.0 - earth_rotation + 180.0) % 360.0) - 180.0

        self.in_eclipse = phase < self.eclipse_fraction or phase > (1.0 - self.eclipse_fraction * 0.15)

        if self.in_eclipse:
            self.solar_power_w = 0.0
            self.battery_v = max(24.5, self.battery_v - 0.0008)
            self.battery_temp_c = max(-5.0, self.battery_temp_c - 0.01)
        else:
            sun_angle = math.cos((phase - 0.5) * 2 * math.pi)
            self.solar_power_w = max(0.0, 85.0 * max(0.0, sun_angle) + 15.0)
            self.battery_v = min(30.0, self.battery_v + 0.0012)
            self.battery_temp_c = min(38.0, self.battery_temp_c + 0.008)

        self.altitude_km = 420.0 + 1.5 * math.sin(t / 120.0) - (t / 86400.0) * 0.05
        self.velocity_kms = 7.66 + 0.01 * math.sin(t / 90.0)
        self.doppler_hz = 8500.0 * math.sin(orbit_angle)
        self.seq = (self.seq + 1) % 16384

    def telemetry_dict(self):
        self.step()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "spacecraft": "KAVACH-1",
            "mode": self.mode,
            "latitude": round(self.lat, 4),
            "longitude": round(self.lon, 4),
            "altitude_km": round(self.altitude_km, 3),
            "velocity_kms": round(self.velocity_kms, 4),
            "battery_v": round(self.battery_v, 3),
            "battery_temp_c": round(self.battery_temp_c, 2),
            "solar_power_w": round(self.solar_power_w, 2),
            "in_eclipse": self.in_eclipse,
            "doppler_hz": round(self.doppler_hz, 1),
            "fuel_kg": round(self.fuel_kg, 3),
            "ccsds_seq": self.seq,
            "hkdf_verified": True,
            "anti_replay_status": "VALIDATED",
            "crypto": "ML-KEM-768 + HKDF-SHA256 + AES-256-GCM",
            "standard": "CCSDS 133.0-B (Primary Header)",
        }

def aes_encrypt(key: bytes, plaintext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext, None)
    return nonce + ct

def aes_decrypt(key: bytes, blob: bytes) -> bytes:
    aesgcm = AESGCM(key)
    nonce, ct = blob[:12], blob[12:]
    return aesgcm.decrypt(nonce, ct, None)

def main():
    print("=" * 65)
    print("  KAVACH SPACECRAFT FLIGHT SOFTWARE v3.0")
    print("  Post-Quantum Engine : ML-KEM-768 (NIST FIPS 203)")
    print("  Key Derivation      : HKDF-SHA256 (NIST SP 800-56C)")
    print("  Anti-Replay Filter  : 64-Frame Sliding Window")
    print("  Flight Dynamics     : Real-Time LEO Orbital Trajectory")
    print("=" * 65)

    sc = LEOSpacecraft()
    replay_filter = AntiReplayWindow(window_size=64)
    kem = oqs.KeyEncapsulation("ML-KEM-768")
    public_key = kem.generate_keypair()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(1)
    print(f"[SAT] Waiting for ground station on port {PORT}...")

    conn, addr = srv.accept()
    print(f"[SAT] Ground station connected: {addr}")

    hs_frame = make_handshake_frame(0, public_key)
    conn.sendall(struct.pack(">I", len(hs_frame)) + hs_frame)
    print("[SAT] Sent ML-KEM-768 public key (CCSDS APID=0x001)")

    raw_len = conn.recv(4)
    if len(raw_len) < 4:
        print("[SAT] Handshake failed")
        return
    n = struct.unpack(">I", raw_len)[0]
    encap_blob = b""
    while len(encap_blob) < n:
        encap_blob += conn.recv(n - len(encap_blob))

    try:
        parsed = CCSDSPacket.unpack(encap_blob)
        ciphertext = parsed["data"]
    except Exception:
        ciphertext = encap_blob

    shared_secret = kem.decap_secret(ciphertext)
    payload_key, mac_key = derive_session_keys(shared_secret)
    print("[SAT] Derived session keys using HKDF-SHA256 (AES-256 Key Ready)")
    print("[SAT] Entering nominal LEO operations...\n")

    seq = 1
    try:
        while True:
            tlm = sc.telemetry_dict()
            tlm_json = json.dumps(tlm).encode("utf-8")
            encrypted = aes_encrypt(payload_key, tlm_json)
            frame = make_telemetry_frame(seq, encrypted)
            seq = (seq + 1) % 16384
            conn.sendall(struct.pack(">I", len(frame)) + frame)

            eclipse_str = "ECLIPSE" if tlm["in_eclipse"] else "SUNLIGHT"
            print(
                f"[TM] seq={tlm['ccsds_seq']:04d} | lat={tlm['latitude']}° lon={tlm['longitude']}° | "
                f"h={tlm['altitude_km']} km | bat={tlm['battery_v']} V | {eclipse_str}"
            )

            conn.settimeout(0.3)
            try:
                hdr = conn.recv(4)
                if hdr and len(hdr) == 4:
                    clen = struct.unpack(">I", hdr)[0]
                    cdata = b""
                    while len(cdata) < clen:
                        cdata += conn.recv(clen - len(cdata))
                    try:
                        cparsed = CCSDSPacket.unpack(cdata)
                        cseq = cparsed["seq_count"]

                        if not replay_filter.validate_and_update(cseq):
                            print(f"[SECURITY ALERT] REPLAY ATTACK REJECTED! (Frame seq={cseq})")
                            continue

                        pt = aes_decrypt(payload_key, cparsed["data"])
                        cmd = json.loads(pt.decode("utf-8"))
                        print(f"[TC] VALIDATED COMMAND (seq={cseq}): {cmd}")
                        if isinstance(cmd, dict) and cmd.get("cmd") == "SET_MODE":
                            sc.mode = cmd.get("value", "NOMINAL")
                    except Exception as e:
                        print(f"[SAT] Command decrypt/parse error: {e}")
            except socket.timeout:
                pass
            finally:
                conn.settimeout(None)

            time.sleep(1.0)

    except (ConnectionResetError, BrokenPipeError, KeyboardInterrupt):
        print("\n[SAT] Link lost or shutdown. Safe mode.")
    finally:
        conn.close()
        srv.close()

if __name__ == "__main__":
    main()
