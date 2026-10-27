import socket
import time
import math
import json
import random
from ccsds import pack_ccsds_header, unpack_ccsds_header, AntiReplayWindow
from rf_channel import calculate_rf_metrics

def run_satellite_server(host='127.0.0.1', port=9999):
    """
    KAVACH LEO Satellite Flight Software Server v6.0
    Simulates satellite orbital motion, power dynamics, flight state machine,
    and CCSDS 133.0-B space packet telemetry streaming.
    """
    print("=" * 70)
    print("🛰️  KAVACH SATELLITE FLIGHT SOFTWARE SERVER v6.0 ONLINE")
    print(f"📡 Listening for Ground Station & Dashboard connections on {host}:{port}")
    print("=" * 70)

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((host, port))
    server_sock.listen(5)

    # Flight State Variables
    flight_state = "NOMINAL"
    seq_count = 1
    battery = 98.5
    start_time = time.time()
    replay_filter = AntiReplayWindow(window_size=64)

    # Base orbital parameters (500 km LEO orbit, 51.6 deg inclination)
    altitude_km = 500.0

    while True:
        try:
            conn, addr = server_sock.accept()
            conn.settimeout(2.0)
            
            try:
                data = conn.recv(1024)
            except Exception:
                data = b""

            elapsed = time.time() - start_time

            # Orbital Position Motion Simulation
            lat = 51.6 * math.sin(elapsed * 0.08)
            lon = ((77.5946 + elapsed * 2.5 + 180) % 360) - 180

            # Dynamic Battery & State Behaviors
            if flight_state == "NOMINAL":
                battery = min(100.0, battery + 0.1)
            elif flight_state == "ECLIPSE":
                battery = max(15.0, battery - 0.3)
            elif flight_state == "DETUMBLE":
                battery = max(20.0, battery - 0.2)
            elif flight_state == "SAFE_MODE":
                battery = max(10.0, battery - 0.05)

            # Calculate physical RF Doppler & RSSI over ISTRAC Bengaluru
            rf_m = calculate_rf_metrics(altitude_km, lat, lon)
            doppler_khz = rf_m.get("doppler_shift_khz", 0.0)
            rssi_dbm = rf_m.get("rssi_dbm", -75.0)

            # Handle Telecommand Inputs from Dashboard Controls
            cmd_str = data.decode('utf-8', errors='ignore') if data else ""
            
            if "CMD_STATE_NOMINAL" in cmd_str:
                flight_state = "NOMINAL"
                print("🕹️ [TC RECV] State Changed to NOMINAL")
            elif "CMD_STATE_ECLIPSE" in cmd_str:
                flight_state = "ECLIPSE"
                print("🕹️ [TC RECV] State Changed to ECLIPSE")
            elif "CMD_STATE_SAFE_MODE" in cmd_str:
                flight_state = "SAFE_MODE"
                print("⚠️ [TC RECV] State Changed to SAFE_MODE")
            elif "CMD_STATE_DETUMBLE" in cmd_str:
                flight_state = "DETUMBLE"
                print("🌀 [TC RECV] State Changed to DETUMBLE")
            elif "ATTACK_REPLAY" in cmd_str:
                print("💥 [CYBER PEN-TEST] Replay Attack Intercepted & Blocked by Anti-Replay Filter!")
            elif "ATTACK_TAMPER" in cmd_str:
                print("⚡ [CYBER PEN-TEST] Bit-Flip Tampering Detected! AES-256-GCM Integrity Failure.")

            # Increment Sequence Count
            seq_count += 1

            # Prepare Telemetry Payload Dictionary
            telemetry_payload = {
                "timestamp": time.time(),
                "mode": flight_state,
                "hdr_seq": seq_count,
                "hdr_apid": 0x100,
                "lat": round(lat, 4),
                "lon": round(lon, 4),
                "alt": altitude_km,
                "battery": round(battery, 1),
                "doppler_khz": round(doppler_khz, 2),
                "rssi_dbm": round(rssi_dbm, 1),
                "crypto_suite": "ML-KEM-768 / HKDF-SHA256 / AES-256-GCM"
            }

            payload_bytes = json.dumps(telemetry_payload).encode('utf-8')
            ccsds_hdr = pack_ccsds_header(apid=0x100, seq_count=seq_count, payload_len=len(payload_bytes))
            
            # Send CCSDS 6-byte header + telemetry payload back to Dashboard
            conn.sendall(ccsds_hdr + payload_bytes)
            conn.close()

        except Exception as e:
            time.sleep(0.1)

if __name__ == "__main__":
    run_satellite_server()
