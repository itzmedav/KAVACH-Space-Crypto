"""
KAVACH Mission Control Dashboard v2.0
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

st.markdown(
    """
<style>
.stApp { background-color: #0b0f19; color: #e0e6ed; }
[data-testid="stSidebar"] { background-color: #111827; }
h1, h2, h3 { color: #38bdf8 !important; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🛡️ KAVACH Mission Control")
st.caption("Post-Quantum LEO Link  •  ML-KEM-768 + AES-256-GCM  •  CCSDS Space Packets")

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
    st.header("Link Control")
    if not st.session_state.connected:
        if st.button("🚀 Connect to Spacecraft", use_container_width=True):
            with st.spinner("ML-KEM-768 handshake..."):
                if connect():
                    st.success("Quantum-safe link established")
                    st.rerun()
    else:
        st.success("🟢 LINK LIVE (ML-KEM-768)")
        if st.button("Disconnect", use_container_width=True):
            try:
                st.session_state.sock.close()
            except Exception:
                pass
            st.session_state.connected = False
            st.rerun()

    st.divider()
    st.subheader("Telecommands")
    if st.session_state.connected:
        if st.button("PING", use_container_width=True):
            send_cmd({"cmd": "PING", "ts": time.time()})
        mode = st.selectbox("Mode", ["NOMINAL", "SAFE", "SCIENCE", "DEORBIT_PREP"])
        if st.button("SET MODE", use_container_width=True):
            send_cmd({"cmd": "SET_MODE", "value": mode})

if not st.session_state.connected:
    st.info("Click **Connect to Spacecraft** in the sidebar. Make sure `satellite.py` is running.")
    st.stop()

tlm = recv_one_tlm()
if tlm:
    st.session_state.tlm_log.append(tlm)
    if len(st.session_state.tlm_log) > 120:
        st.session_state.tlm_log = st.session_state.tlm_log[-120:]

if not st.session_state.tlm_log:
    st.warning("Waiting for first CCSDS telemetry frame...")
    time.sleep(0.5)
    st.rerun()

latest = st.session_state.tlm_log[-1]
df = pd.DataFrame(st.session_state.tlm_log)

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Altitude", f"{latest.get('altitude_km', 0):.2f} km")
c2.metric("Velocity", f"{latest.get('velocity_kms', 0):.3f} km/s")
c3.metric("Battery", f"{latest.get('battery_v', 0):.2f} V")
c4.metric("Solar Power", f"{latest.get('solar_power_w', 0):.1f} W")
c5.metric("Temp", f"{latest.get('battery_temp_c', 0):.1f} °C")
eclipse = latest.get("in_eclipse", False)
c6.metric("Orbit Phase", "🌑 ECLIPSE" if eclipse else "☀️ SUNLIGHT")

st.divider()

fig = make_subplots(
    rows=2,
    cols=2,
    subplot_titles=("Altitude (km)", "Battery Voltage (V)", "Solar Power (W)", "Doppler Shift (Hz)"),
    vertical_spacing=0.12,
)
fig.add_trace(go.Scatter(y=df["altitude_km"], name="Alt", line=dict(color="#38bdf8")), row=1, col=1)
fig.add_trace(go.Scatter(y=df["battery_v"], name="Batt", line=dict(color="#4ade80")), row=1, col=2)
fig.add_trace(go.Scatter(y=df["solar_power_w"], name="Solar", line=dict(color="#facc15")), row=2, col=1)
if "doppler_hz" in df.columns:
    fig.add_trace(go.Scatter(y=df["doppler_hz"], name="Doppler", line=dict(color="#f472b6")), row=2, col=2)

fig.update_layout(
    height=520,
    paper_bgcolor="#0b0f19",
    plot_bgcolor="#111827",
    font_color="#e0e6ed",
    showlegend=False,
    margin=dict(l=20, r=20, t=40, b=20),
)
fig.update_xaxes(showgrid=True, gridcolor="#1f2937")
fig.update_yaxes(showgrid=True, gridcolor="#1f2937")
st.plotly_chart(fig, use_container_width=True)

with st.expander("Latest CCSDS Frame + Decrypted Telemetry", expanded=False):
    st.json(latest)

st.caption(
    f"CCSDS seq={latest.get('_ccsds_seq', latest.get('ccsds_seq', '?'))}  |  "
    f"APID={latest.get('_ccsds_apid', 0x100)}  |  Crypto=ML-KEM-768+AES-256-GCM  |  "
    f"Frames logged={len(st.session_state.tlm_log)}"
)

time.sleep(0.8)
st.rerun()
