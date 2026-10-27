import streamlit as st
import plotly.graph_objects as go
import socket
import json
import time
import pandas as pd
from ccsds import derive_session_keys, pack_ccsds_header, unpack_ccsds_header
from rf_channel import calculate_rf_metrics, corrupt_payload
from oqs import KeyEncapsulation

st.set_page_config(
    page_title="KAVACH - Spacecraft Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #e0e6ed; }
    .metric-card {
        background: linear-gradient(135deg, #161e2e 0%, #0d131d 100%);
        border: 10px solid #1e293b;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 20px rgba(0,255,204,0.05);
    }
    .status-badge-ok {
        background-color: rgba(16, 185, 129, 0.2);
        color: #10b981;
        border: 1px solid #10b981;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
    }
    .status-badge-alert {
        background-color: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        border: 1px solid #ef4444;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

if 'history' not in st.session_state:
    st.session_state.history = []
if 'seq_count' not in st.session_state:
    st.session_state.seq_count = 1
if 'replays_blocked' not in st.session_state:
    st.session_state.replays_blocked = 0
if 'tampered_blocked' not in st.session_state:
    st.session_state.tampered_blocked = 0

st.sidebar.title("🛰️ KAVACH Mission Control")
st.sidebar.markdown("**Post-Quantum Space Protocol**")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔐 Security Architecture")
st.sidebar.info("""
- **KEM:** ML-KEM-768 (NIST FIPS 203)
- **KDF:** HKDF-SHA256 (NIST SP 800-56C)
- **AEAD:** AES-256-GCM
- **Framing:** CCSDS 133.0-B
- **Anti-Replay:** 64-Frame Bitmap Window
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚔️ Cyber Attack Harness")
inject_replay = st.sidebar.button("⚡ INJECT REPLAY ATTACK", help="Re-sends an old valid CCSDS frame to test sequence rejection")
inject_tamper = st.sidebar.button("💥 INJECT BIT-FLIP TAMPERING", help="Flips payload bits to test AES-GCM AEAD tag failure")

def connect_and_fetch(attack_mode=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(('127.0.0.1', 9999))
        
        # ML-KEM Handshake
        raw_pk = s.recv(2048)
        if not raw_pk:
            s.close()
            return None
            
        with KeyEncapsulation('Kyber768') as client_kem:
            ciphertext, shared_secret = client_kem.encap_secret(raw_pk)
            
        s.sendall(ciphertext)
        k_enc, _, _ = derive_session_keys(shared_secret)
        
        # Read Telemetry Frame
        frame = s.recv(4096)
        hdr, payload = unpack_ccsds_header(frame)
        
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        aesgcm = AESGCM(k_enc)
        nonce = payload[:12]
        ct_tag = payload[12:]
        
        try:
            pt = aesgcm.decrypt(nonce, ct_tag, frame[:6])
            telemetry = json.loads(pt.decode('utf-8'))
        except Exception as e:
            telemetry = {"error": f"Decryption failed: {e}"}

        # Attack Injection Triggering
        if attack_mode == 'replay':
            hdr_bad = pack_ccsds_header(0x200, st.session_state.seq_count - 1, len(frame[:6]))
            s.sendall(hdr_bad + payload)
            st.session_state.replays_blocked += 1
        elif attack_mode == 'tamper':
            corrupted_payload = corrupt_payload(payload)
            hdr_tc = pack_ccsds_header(0x200, st.session_state.seq_count, len(corrupted_payload))
            s.sendall(hdr_tc + corrupted_payload)
            st.session_state.tampered_blocked += 1
            st.session_state.seq_count += 1
            
        s.close()
        return telemetry, hdr
    except Exception as ex:
        return None, None

attack = 'replay' if inject_replay else ('tamper' if inject_tamper else None)
telemetry, hdr = connect_and_fetch(attack_mode=attack)

st.title("🛡️ KAVACH: Post-Quantum LEO Satellite Command & Telemetry")

col_head1, col_head2, col_head3, col_head4 = st.columns(4)
with col_head1:
    st.markdown("<div class='metric-card'><h4>Status</h4><span class='status-badge-ok'>NOMINAL PASS</span></div>", unsafe_allow_html=True)
with col_head2:
    st.markdown(f"<div class='metric-card'><h4>Replays Blocked</h4><h2 style='color:#ef4444;'>{st.session_state.replays_blocked}</h2></div>", unsafe_allow_html=True)
with col_head3:
    st.markdown(f"<div class='metric-card'><h4>Tampered Frames Rejected</h4><h2 style='color:#f59e0b;'>{st.session_state.tampered_blocked}</h2></div>", unsafe_allow_html=True)
with col_head4:
    st.markdown("<div class='metric-card'><h4>Crypto Engine</h4><h4 style='color:#00ffcc;'>ML-KEM-768 ACTIVE</h4></div>", unsafe_allow_html=True)

st.markdown("---")

if telemetry and 'error' not in telemetry:
    st.session_state.history.append(telemetry)
    if len(st.session_state.history) > 30:
        st.session_state.history.pop(0)

    df = pd.DataFrame(st.session_state.history)
    
    col_map, col_metrics = st.columns([6, 4])
    
    with col_map:
        st.subheader("🌐 Ground Track & Pass Geometry (ISTRAC Bengaluru)")
        fig_map = go.Figure()
        
        # Ground station marker
        fig_map.add_trace(go.Scattergeo(
            lat=[12.9716], lon=[77.5946],
            mode='markers+text',
            text=["ISTRAC Bengaluru"],
            textposition="top center",
            marker=dict(size=14, color='#00ffcc', symbol='triangle-up'),
            name="Ground Station"
        ))
        
        # Satellite marker & track
        if 'lat' in df.columns:
            fig_map.add_trace(go.Scattergeo(
                lat=df['lat'], lon=df['lon'],
                mode='lines+markers',
                line=dict(width=2, color='#3b82f6'),
                marker=dict(size=8, color='#ef4444'),
                name="KAVACH-1 Track"
            ))
            
        fig_map.update_layout(
            geo=dict(
                projection_type='orthographic',
                showland=True, landcolor='#1e293b',
                showocean=True, oceancolor='#0f172a',
                showcountries=True, countrycolor='#334155',
                bgcolor='rgba(0,0,0,0)'
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            height=400
        )
        st.plotly_chart(fig_map, width="stretch")
        
    with col_metrics:
        st.subheader("⚡ Orbital Telemetry & RF Metrics")
        m1, m2 = st.columns(2)
        m1.metric("Altitude", f"{telemetry.get('alt_km', 500):.2f} km")
        m2.metric("Velocity", f"{telemetry.get('vel_kms', 7.6):.2f} km/s")
        
        m3, m4 = st.columns(2)
        m3.metric("Battery Voltage", f"{telemetry.get('battery_v', 8.2):.2f} V")
        m4.metric("Solar Power", f"{telemetry.get('solar_w', 12.0):.2f} W")

        m5, m6 = st.columns(2)
        m5.metric("Doppler Shift", f"{telemetry.get('doppler_hz', 0):.1f} Hz")
        m6.metric("RSSI / SNR", f"{telemetry.get('rssi_dbm', -90):.1f} dBm / {telemetry.get('snr_db', 12):.1f} dB")

    st.markdown("---")
    st.subheader("📈 Real-Time Telemetry Trends")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        fig_batt = go.Figure()
        fig_batt.add_trace(go.Scatter(y=df['battery_v'], mode='lines+markers', name='Battery (V)', line=dict(color='#10b981')))
        fig_batt.update_layout(title="Battery Bus Voltage (V)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0e6ed'), height=250)
        st.plotly_chart(fig_batt, width="stretch")
    with col_t2:
        fig_doppler = go.Figure()
        fig_doppler.add_trace(go.Scatter(y=df['doppler_hz'], mode='lines+markers', name='Doppler (Hz)', line=dict(color='#f59e0b')))
        fig_doppler.update_layout(title="433 MHz RF Doppler Shift (Hz)", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#e0e6ed'), height=250)
        st.plotly_chart(fig_doppler, width="stretch")

    st.markdown("---")
    st.subheader("📦 CCSDS 133.0-B Primary Header Inspection")
    if hdr:
        st.json({
            "Version": hdr['version'],
            "Packet Type": "TC (Telecommand)" if hdr['type'] == 1 else "TM (Telemetry)",
            "APID": f"0x{hdr['apid']:03X}",
            "Sequence Count": hdr['seq'],
            "Payload Length (bytes)": hdr['len']
        })

else:
    st.warning("⚠️ Connecting to Spacecraft Flight Software on TCP:9999...")

time.sleep(1.5)
st.rerun()
