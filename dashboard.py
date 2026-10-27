import streamlit as st
import socket
import base64
import json
import time
import oqs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import plotly.graph_objects as go
import pandas as pd

# Streamlit Page Config
st.set_page_config(page_title="KAVACH Real Control", page_icon="🛰️", layout="wide")

# Custom Styling
st.markdown("""
<style>
    .main { background-color: #0B0E14; }
    .stMetric { background-color: #161B22; padding: 15px; border-radius: 10px; border: 1px solid #30363D; }
    h1, h2, h3 { color: #58A6FF; }
</style>
""", unsafe_allow_html=True)

st.title("🛰️ KAVACH — Real-Time Post-Quantum Mission Control")
st.caption("Connected to Native C++ liboqs Engine | NIST FIPS 203 (ML-KEM-768) + AES-256-GCM")

KEM_ALG = "ML-KEM-768" if "ML-KEM-768" in oqs.get_enabled_kem_mechanisms() else "Kyber768"

# ─── SOCKET & CRYPTO STATE MANAGEMENT ───
if "sock" not in st.session_state:
    st.session_state.sock = None
if "aes" not in st.session_state:
    st.session_state.aes = None
if "nonce_counter" not in st.session_state:
    st.session_state.nonce_counter = 0
if "connected" not in st.session_state:
    st.session_state.connected = False
if "history" not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=["Time", "Temp", "Voltage"])

def connect_and_handshake():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', 9999))
        
        # Handshake
        hello = sock.recv(1024).decode().strip()
        if "HELLO" in hello:
            sock.send(b"KAVACH_ACK\n")
            
        # Key Exchange
        pk_line = sock.recv(8192).decode().strip()
        public_key = base64.b64decode(pk_line.split("PK:")[1])
        
        with oqs.KeyEncapsulation(KEM_ALG) as kem:
            ciphertext, shared_secret = kem.encap_secret(public_key)
            
        sock.send(b"CT:" + base64.b64encode(ciphertext) + b"\n")
        done = sock.recv(1024).decode().strip()
        
        if "DONE" in done:
            st.session_state.aes = AESGCM(shared_secret)
            st.session_state.sock = sock
            st.session_state.connected = True
            return True, shared_secret[:8].hex()
    except Exception as e:
        return False, str(e)
    return False, "Failed"

def send_real_command(cmd_str):
    if not st.session_state.connected or not st.session_state.sock:
        return None
    try:
        st.session_state.nonce_counter += 1
        nonce = st.session_state.nonce_counter.to_bytes(12, 'big')
        ct = st.session_state.aes.encrypt(nonce, cmd_str.encode(), None)
        packet = base64.b64encode(nonce + ct).decode()
        
        # Transmit over socket to satellite.py
        st.session_state.sock.send(f"ENC:{packet}\n".encode())
        
        # Receive encrypted response
        resp = st.session_state.sock.recv(8192).decode().strip()
        if resp.startswith("ENC:"):
            raw = base64.b64decode(resp[4:])
            r_nonce, r_ct = raw[:12], raw[12:]
            decrypted = st.session_state.aes.decrypt(r_nonce, r_ct, None).decode()
            return decrypted
    except Exception as e:
        st.session_state.connected = False
        return f"ERROR: {e}"
    return None

# ─── SIDEBAR ───
st.sidebar.title("🛰️ Link Control")
if not st.session_state.connected:
    if st.sidebar.button("🔌 Establish ML-KEM-768 Link"):
        success, info_str = connect_and_handshake()
        if success:
            st.sidebar.success(f"CONNECTED! Shared Secret: {info_str}...")
            st.rerun()
        else:
            st.sidebar.error(f"Connection Failed: Ensure satellite.py is running! ({info_str})")
else:
    st.sidebar.success("🟢 ML-KEM-768 LINK ACTIVE")
    st.sidebar.info(f"Engine: {KEM_ALG}")
    st.sidebar.text("Public Key: 1184 Bytes")
    st.sidebar.text("Data Cipher: AES-256-GCM")
    if st.sidebar.button("Disconnect Link"):
        st.session_state.sock.close()
        st.session_state.connected = False
        st.rerun()

# ─── METRICS BAR ───
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Spacecraft Health", "NOMINAL" if st.session_state.connected else "OFFLINE")
with m2:
    st.metric("Post-Quantum Key Exch", KEM_ALG, "NIST FIPS 203")
with m3:
    st.metric("Payload Cipher", "AES-256-GCM", "Active")
with m4:
    st.metric("Link Connection", "ONLINE" if st.session_state.connected else "DISCONNECTED")

st.markdown("---")

# ─── MAIN DASHBOARD ───
col_telemetry, col_controls = st.columns([2, 1])

with col_telemetry:
    st.subheader("📊 Live Encrypted Telemetry Feed")
    
    if st.button("📡 Fetch Real Encrypted Telemetry Frame") and st.session_state.connected:
        raw_resp = send_real_command("CMD:GET_TELEMETRY")
        if raw_resp and raw_resp.startswith("TEL:"):
            json_data = json.loads(raw_resp[4:])
            now = time.strftime("%H:%M:%S")
            new_entry = {
                "Time": [now],
                "Temp": [json_data.get("temp_c", 22.0)],
                "Voltage": [json_data.get("battery_v", 3.3)]
            }
            st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame(new_entry)]).tail(15)
            st.success(f"Decrypted Raw Payload: {raw_resp[4:]}")
    
    # Plot Chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=st.session_state.history["Time"], y=st.session_state.history["Temp"], name="Temperature (°C)", line=dict(color="#FF4B4B", width=3)))
    fig.add_trace(go.Scatter(x=st.session_state.history["Time"], y=st.session_state.history["Voltage"], name="Bus Voltage (V)", line=dict(color="#00D26A", width=3)))
    fig.update_layout(template="plotly_dark", height=320, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, width="stretch")

with col_controls:
    st.subheader("⚡ Ground Station Commands")
    
    cmd_choice = st.selectbox("Select Payload:", ["CMD:GET_TELEMETRY", "CMD:GET_STATUS", "CMD:PING"])
    
    if st.button("🚀 Transmit Encrypted Payload"):
        if st.session_state.connected:
            with st.spinner("Encrypting with ML-KEM-768 derived key..."):
                decrypted_response = send_real_command(cmd_choice)
                time.sleep(0.2)
                st.code(f"RESPONSE FROM SATELLITE:\n{decrypted_response}", language="json")
        else:
            st.error("Connect to satellite first using the sidebar button!")