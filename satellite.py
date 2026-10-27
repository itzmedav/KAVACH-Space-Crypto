import socket
import json
import time
import math
from oqs import KeyEncapsulation
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from ccsds import pack_ccsds_header, unpack_ccsds_header, derive_session_keys, AntiReplayWindow
from rf_channel import calculate_rf_metrics

def run_satellite_server(port=9999):
    anti_replay = AntiReplayWindow(window_size=64)
    orbital_step = 0
    
    sat_state = {
        "mode": "NOMINAL",
        "eclipse": False,
        "detumbling": False,
        "angular_velocity_dps": 2.4
    }

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', port))
    srv.listen(5)

    print("=================================================================")
    print("  KAVACH SPACECRAFT FLIGHT SOFTWARE v5.0 (STATE MACHINE ENGINE)")
    print("  Post-Quantum Engine : ML-KEM-768 (NIST FIPS 203)")
    print("  Key Derivation      : HKDF-SHA256 (NIST SP 800-56C)")
    print("  Anti-Replay Filter  : 64-Frame Sliding Bitmap Window")
    print("=================================================================\n")
    print(f"[SAT] Listening for Ground Station on port {port}...")

    while True:
        try:
            conn, addr = srv.accept()
            print(f"\n[SAT] Ground Station connected: {addr}")

            with KeyEncapsulation('Kyber768') as kem:
                public_key = kem.generate_keypair()
                conn.sendall(public_key)

                ciphertext = conn.recv(2048)
                if not ciphertext:
                    conn.close()
                    continue

                shared_secret = kem.decap_secret(ciphertext)
                k_enc, _ = derive_session_keys(shared_secret)
                print("[SAT] Ephemeral Handshake Complete. AES-256 Session Key Derived.")

                orbital_step += 1
                t = orbital_step * 0.1
                lat = 12.9716 + 15.0 * math.sin(t * 0.2)
                lon = 77.5946 + 25.0 * math.cos(t * 0.2)
                alt_km = 508.4 + 1.2 * math.sin(t * 0.5)
                vel_kms = 7.61 - 0.01 * math.sin(t * 0.5)

                if sat_state["eclipse"]:
                    solar_w = 0.0
                    battery_v = max(6.8, 8.4 - (orbital_step % 20) * 0.08)
                    temp_c = max(-25.0, 18.0 - (orbital_step % 20) * 1.5)
                else:
                    solar_w = 14.5 + 2.1 * math.cos(t * 0.3)
                    battery_v = 8.2 + 0.2 * math.sin(t * 0.3)
                    temp_c = 22.5 + 4.0 * math.sin(t * 0.1)

                if sat_state["detumbling"]:
                    sat_state["angular_velocity_dps"] = max(0.1, sat_state["angular_velocity_dps"] * 0.7)
                    if sat_state["angular_velocity_dps"] <= 0.2:
                        sat_state["detumbling"] = False

                rf_metrics = calculate_rf_metrics(alt_km)

                telemetry_payload = {
                    "step": orbital_step,
                    "mode": sat_state["mode"],
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "alt_km": round(alt_km, 2),
                    "vel_kms": round(vel_kms, 3),
                    "battery_v": round(battery_v, 2),
                    "solar_w": round(solar_w, 2),
                    "temp_c": round(temp_c, 1),
                    "ang_vel": round(sat_state["angular_velocity_dps"], 2),
                    "eclipse": sat_state["eclipse"],
                    "doppler_hz": rf_metrics["doppler_hz"],
                    "rssi_dbm": rf_metrics["rssi_dbm"],
                    "snr_db": rf_metrics["snr_db"]
                }

                payload_bytes = json.dumps(telemetry_payload).encode('utf-8')
                aesgcm = AESGCM(k_enc)
                nonce = bytes([orbital_step % 256] * 12)
                
                header_bytes = pack_ccsds_header(apid=0x100, seq_count=orbital_step, payload_len=len(payload_bytes))
                ciphertext_and_tag = aesgcm.encrypt(nonce, payload_bytes, header_bytes)

                conn.sendall(header_bytes + nonce + ciphertext_and_tag)

                tc_frame = conn.recv(4096)
                if tc_frame and len(tc_frame) >= 6:
                    hdr_tc, payload_tc = unpack_ccsds_header(tc_frame)

                    if not anti_replay.is_valid(hdr_tc["seq"]):
                        print(f"[🚨 REPLAY ATTACK BLOCKED] Sequence count {hdr_tc['seq']} rejected by Anti-Replay Filter!")
                    else:
                        try:
                            nonce_tc = payload_tc[:12]
                            ct_tc = payload_tc[12:]
                            pt_tc = aesgcm.decrypt(nonce_tc, ct_tc, tc_frame[:6])
                            cmd_json = json.loads(pt_tc.decode('utf-8'))
                            
                            cmd = cmd_json.get("cmd")
                            print(f"[TC AUTHENTICATED] Valid Command Received (Seq={hdr_tc['seq']}): {cmd}")

                            if cmd == "CMD_SAFE_MODE":
                                sat_state["mode"] = "SAFE_MODE"
                            elif cmd == "CMD_NOMINAL":
                                sat_state["mode"] = "NOMINAL"
                                sat_state["eclipse"] = False
                            elif cmd == "CMD_ECLIPSE":
                                sat_state["eclipse"] = not sat_state["eclipse"]
                            elif cmd == "CMD_DETUMBLE":
                                sat_state["detumbling"] = True
                                sat_state["angular_velocity_dps"] = 8.5

                        except Exception:
                            print("[🚨 SECURITY ALERT] ATTACK BLOCKED: AES-GCM Tag Mismatch / Bit-Flip Tampering Detected!")

                conn.close()

        except Exception as e:
            print(f"[SAT ERROR] Exception: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_satellite_server()
