"""
KAVACH Mission Control Dashboard v2.1 (Sleek Space-Grade UI)
Streamlit + Plotly | CCSDS + LEO Telemetry | ML-KEM-768
"""
import streamlit as st
import socket
import struct
import json
import time
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import oqs
import os
from ccsds import CCSDSPacket, make_telecommand_frame, make_handshake_frame

st.set_page_config(page_title="KAVACH Mission Control", page_icon="🛡️", layout="wide")

# CSS Styling - Spacecraft Cockpit Theme
st.markdown(
    """
<style>
/* Remove Streamlit default white top bar */
header[data-testid="stHeader"] {
    background-color: transparent !important;
    display: none !important;
}
.stAppViewContainer {
    padding-top: 0rem !important;
}
.stApp {
    background-color: #060a12 !important;
    color: #f1f5f9;
}
/* Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: #0b1120 !important;
    border-right: 1px solid #1e293b !important;
}

/* Metric Cards */
div[data-testid="stMetric"] {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border: 1px solid #334155;
    padding: 14px 18px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
div[data-testid="stMetric"]:hover {
    border-color: #38bdf8;
    transform: translateY(-2px);
}
div[data-testid="stMetricValue"] {
    color: #38bdf8 !important;
    font-weight: 800 !important;
    font-size: 1.7rem !important;
    font-family: 'Segoe UI', monospace;
}
div[data-testid="stMetricLabel"] {
    color: #94a3b8 !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Custom Sleek Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important;
    color: #38bdf8 !important;
    border: 1px solid #0284c7 !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em;
    padding: 0.5rem 1rem !important;
    transition: all 0.3s ease !important;
    width: 100%;
}
.stButton > button:hover {
    background: #0284c7 !important;
    color: #ffffff !important;
    box-shadow: 0 0 15px rgba(56, 189, 248, 0.6) !important;
    border-color: #38bdf8 !important;
}

/* Selectbox Dropdowns */
div[data-baseweb="select"] {
    background-color: #0f172a !important;
    border-radius: 8px !important;
    border: 1px solid #334155 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# Header Banner
st.markdown("""
<div style="background: linear-gradient(90deg, #0b1120 0%, #1e293b 100%); padding: 18px 24px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;">
    <div>
        <h1 style="margin:0; font-size: 2.2rem; font-weight: 800; color: #38bdf8; display: inline-block;">🛡️ KAVACH</h1>
        <span style="font-size: 1.1rem; color: #94a3b8; margin-left: 12px; font-weight: 600;">MISSION CONTROL • POST-QUANTUM LEO LINK</span>
    </div>
    <div style="background: #0284c722; border: 1px solid #0284c7; color: #38bdf8; padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; font-weight: 700;">
        FIPS 203 (ML-KEM-768) + CCSDS
    </div>
</div>
""", unsafe_allow_html=True)

SERVER = ("127.0.0.1", 9999)

if "connected" not in st.session_state:
    st.session_state.connected = False
    st.session_state.sock = None
    st.session_state.session_key = None
    st.session_state.tlm_log = []
    st.session_state.seq = 1

def aes_encrypt(key, pt):
    aes = AESGCM(key)
    nonce = os.urandom(12)
    return nonce + aes.encrypt(nonce, pt, None)

def aes_decrypt(key, blob):
    aes = AESGCM(key)
    return aes.decrypt(blob[:12], blob[12:], None)

def connect():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect(SERVER)

        raw_len = s.recv(4)
        n = struct.unpack(">I", raw_len)[0]
        hs = b""
        while len(hs) < n:
            hs += s.recv(n - len(hs))

        try:
            parsed = CCSDSPacket.unpack(hs)
            pk = parsed["data"]
        except Exception:
            pk = hs

        with oqs.KeyEncapsulation("ML-KEM-768") as kem:
            ct, ss = kem.encap_secret(pk)

        session_key = ss[:32]
        frame = make_handshake_frame(0, ct)
        s.sendall(struct.pack(">I", len(frame)) + frame)
        s.settimeout(1.0)

        st.session_state.sock = s
        st.session_state.session_key = session_key
        st.session_state.connected = True
        return True
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return False

def recv_one_tlm():
    s = st.session_state.sock
    key = st.session_state.session_key
    try:
        hdr = s.recv(4)
        if not hdr or len(hdr) < 4:
            return None
        n = struct.unpack(">I", hdr)[0]
        data = b""
        while len(data) < n:
            chunk = s.recv(n - len(data))
            if not chunk:
                return None
            data += chunk
        parsed = CCSDSPacket.unpack(data)
        pt = aes_decrypt(key, parsed["data"])
        tlm = json.loads(pt.decode("utf-8"))
        tlm["_ccsds_apid"] = parsed["apid"]
        tlm["_ccsds_seq"] = parsed["seq_count"]
        return tlm
    except socket.timeout:
        return None
    except Exception:
        return None

def send_cmd(cmd_dict):
    s = st.session_state.sock
    key = st.session_state.session_key
    blob = aes_encrypt(key, json.dumps(cmd_dict).encode())
    frame = make_telecommand_frame(st.session_state.seq, blob)
    st.session_state.seq = (st.session_state.seq + 1) % 16384
    s.sendall(struct.pack(">I", len(frame)) + frame)

with st.sidebar:
    st.markdown("<h3 style='color:#38bdf8; margin-top:0;'>LINK STATUS</h3>", unsafe_allow_html=True)
    if not st.session_state.connected:
        if st.button("🚀 CONNECT LINK", use_container_width=True):
            with st.spinner("Executing ML-KEM-768 Handshake..."):
                if connect():
                    st.success("Quantum Link Established")
                    st.rerun()
    else:
        st.markdown("""
        <div style='background:#10b98122; border:1px solid #10b981; color:#34d399; padding:10px; border-radius:8px; text-align:center; font-weight:700; margin-bottom:12px;'>
            🟢 LINK LIVE (ML-KEM-768)
        </div>
        """, unsafe_allow_html=True)
        if st.button("DISCONNECT", use_container_width=True):
            try:
                st.session_state.sock.close()
            except Exception:
                pass
            st.session_state.connected = False
            st.rerun()

    st.markdown("<hr style='border-color:#1e293b;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#38bdf8;'>TELECOMMANDS</h3>", unsafe_allow_html=True)
    if st.session_state.connected:
        if st.button("📡 SEND PING", use_container_width=True):
            send_cmd({"cmd": "PING", "ts": time.time()})
        mode = st.selectbox("Spacecraft Mode", ["NOMINAL", "SAFE", "SCIENCE", "DEORBIT_PREP"])
        if st.button("⚡ EXECUTE MODE CHANGE", use_container_width=True):
            send_cmd({"cmd": "SET_MODE", "value": mode})

if not st.session_state.connected:
    st.info("Click **🚀 CONNECT LINK** in the left sidebar to initialize ML-KEM-768 key exchange.")
    st.stop()

tlm = recv_one_tlm()
if tlm:
    st.session_state.tlm_log.append(tlm)
    if len(st.session_state.tlm_log) > 120:
        st.session_state.tlm_log = st.session_state.tlm_log[-120:]

if not st.session_state.tlm_log:
    st.warning("Receiving CCSDS telemetry stream...")
    time.sleep(0.5)
    st.rerun()

latest = st.session_state.tlm_log[-1]
df = pd.DataFrame(st.session_state.tlm_log)

# Metrics Grid
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Altitude", f"{latest.get('altitude_km', 0):.2f} km")
c2.metric("Velocity", f"{latest.get('velocity_kms', 0):.3f} km/s")
c3.metric("Battery", f"{latest.get('battery_v', 0):.2f} V")
c4.metric("Solar Power", f"{latest.get('solar_power_w', 0):.1f} W")
c5.metric("Temp", f"{latest.get('battery_temp_c', 0):.1f} °C")
eclipse = latest.get("in_eclipse", False)
c6.metric("Orbit Phase", "🌑 ECLIPSE" if eclipse else "☀️ SUNLIGHT")

st.markdown("<br>", unsafe_allow_html=True)

# Plotly Charts
fig = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=("ALTITUDE DECAY (KM)", "BATTERY VOLTAGE (V)", "SOLAR ARRAY POWER (W)", "DOPPLER FREQUENCY SHIFT (HZ)"),
    vertical_spacing=0.15,
)
fig.add_trace(go.Scatter(y=df["altitude_km"], name="Alt", line=dict(color="#38bdf8", width=3)), row=1, col=1)
fig.add_trace(go.Scatter(y=df["battery_v"], name="Batt", line=dict(color="#4ade80", width=3)), row=1, col=2)
fig.add_trace(go.Scatter(y=df["solar_power_w"], name="Solar", line=dict(color="#facc15", width=3)), row=2, col=1)
if "doppler_hz" in df.columns:
    fig.add_trace(go.Scatter(y=df["doppler_hz"], name="Doppler", line=dict(color="#f472b6", width=3)), row=2, col=2)

fig.update_layout(
    height=480,
    paper_bgcolor="#060a12",
    plot_bgcolor="#0b1120",
    font=dict(color="#cbd5e1", family="Segoe UI, sans-serif"),
    showlegend=False,
    margin=dict(l=10, r=10, t=30, b=10),
)
fig.update_xaxes(showgrid=True, gridcolor="#1e293b", zeroline=False)
fig.update_yaxes(showgrid=True, gridcolor="#1e293b", zeroline=False)
st.plotly_chart(fig, use_container_width=True)

with st.expander("🔍 INSPECT CCSDS FRAME & DECRYPTED PAYLOAD", expanded=False):
    st.json(latest)

st.caption(
    f"CCSDS FRAME SEQ={latest.get('_ccsds_seq', latest.get('ccsds_seq', '?'))}  |  "
    f"APID={hex(latest.get('_ccsds_apid', 0x100))}  |  KEY=AES-256-GCM (ML-KEM-768 ESTABLISHED)  |  "
    f"BUFFER={len(st.session_state.tlm_log)} FRAMES"
)

time.sleep(0.8)
st.rerun()
