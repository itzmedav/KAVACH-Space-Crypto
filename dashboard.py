import streamlit as st
import socket
import time
import json
import os
import math
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from ccsds import unpack_ccsds_header
from rf_channel import calculate_rf_metrics
from rf_spectrum import RFSpectrumAnalyzer
from pitch_deck import render_pitch_deck
import audit_report

# Streamlit Page Config
st.set_page_config(
    page_title="KAVACH Space Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-Tech Aerospace CSS Styling
st.markdown("""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;600;700;800&display=swap">

<style>
    /* Global Background & Typography */
    .stApp {
        background-color: #04070d;
        color: #d0d7de;
        font-family: 'Inter', sans-serif;
    }
    
    /* Remove default Streamlit top padding */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #070c16 !important;
        border-right: 1px solid #142032 !important;
    }

    /* Header Banner */
    .hero-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(135deg, #091322 0%, #050a12 100%);
        border: 1px solid #1b2e4b;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    .hero-title {
        font-family: 'Inter', sans-serif;
        font-size: 22px;
        font-weight: 800;
        color: #ffffff;
        letter-spacing: -0.5px;
        display: flex;
        align-items: center;
        gap: 12px;
    }

    .hero-subtitle {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        color: #00F0FF;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* Status Pulse Animation */
    .status-badge-online {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(0, 255, 102, 0.08);
        border: 1px solid rgba(0, 255, 102, 0.3);
        color: #00FF66;
        padding: 6px 14px;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        font-weight: 600;
    }

    .status-badge-offline {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255, 75, 75, 0.08);
        border: 1px solid rgba(255, 75, 75, 0.3);
        color: #FF4B4B;
        padding: 6px 14px;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        font-weight: 600;
    }

    .pulse-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #00FF66;
        box-shadow: 0 0 10px #00FF66;
        animation: pulse-green 2s infinite;
    }

    @keyframes pulse-green {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 102, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(0, 255, 102, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(0, 255, 102, 0); }
    }

    /* Modern Glassmorphic Metric Cards */
    .cockpit-card {
        background: #09111e;
        border: 1px solid #16263d;
        border-radius: 10px;
        padding: 14px 18px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        transition: all 0.2s ease-in-out;
    }

    .cockpit-card:hover {
        border-color: #00F0FF;
        transform: translateY(-2px);
    }

    .card-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        color: #7d8ea3;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin-bottom: 6px;
    }

    .card-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 24px;
        font-weight: 700;
        color: #00F0FF;
    }

    .card-unit {
        font-size: 12px;
        color: #8c9ba5;
        font-weight: 400;
        margin-left: 4px;
    }

    /* Custom Streamlit Buttons */
    .stButton>button {
        background: #0b172a !important;
        color: #00F0FF !important;
        border: 1px solid #1a3254 !important;
        border-radius: 8px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-weight: 600 !important;
        font-size: 12px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
    }

    .stButton>button:hover {
        background: #00F0FF !important;
        color: #04070d !important;
        border-color: #00F0FF !important;
        box-shadow: 0 0 15px rgba(0, 240, 255, 0.4) !important;
    }
</style>
""", unsafe_allow_html=True)

# State Management
if 'rf_analyzer' not in st.session_state:
    st.session_state.rf_analyzer = RFSpectrumAnalyzer()

if 'history_lat' not in st.session_state:
    st.session_state.history_lat = []
    st.session_state.history_lon = []

if 'last_telemetry' not in st.session_state:
    st.session_state.last_telemetry = None

if 'cmd_trigger' not in st.session_state:
    st.session_state.cmd_trigger = None

# Sidebar Controls
st.sidebar.markdown("""
<div style="text-align: center; padding: 10px 0;">
    <h2 style="color:#00F0FF; font-family:'IBM Plex Mono'; font-size:20px; font-weight:700; margin:0;">KAVACH</h2>
    <div style="color:#7d8ea3; font-size:11px; letter-spacing:1px; font-family:'IBM Plex Mono';">POST-QUANTUM CRYPTO</div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "SELECT VIEW MODE",
    ["🛰️ Real-Time Cockpit", "📊 Live 433 MHz RF Waterfall", "🛡️ Automated 1,000-Frame Audit", "🎤 Competition Pitch Deck"],
    index=0
)

# -------------------------------------------------------------------------
# VIEW 1: COMPETITION PITCH DECK MODE
# -------------------------------------------------------------------------
if app_mode == "🎤 Competition Pitch Deck":
    render_pitch_deck()

# -------------------------------------------------------------------------
# VIEW 2: AUTOMATED 1,000-FRAME AUDIT
# -------------------------------------------------------------------------
elif app_mode == "🛡️ Automated 1,000-Frame Audit":
    st.markdown("""
    <div class="hero-header">
        <div>
            <div class="hero-title">🛡️ Automated 1,000-Frame Security Audit</div>
            <div class="hero-subtitle">High-Throughput Cyber Attack Campaign & PDF Audit Report Generator</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_audit1, col_audit2 = st.columns([1, 2])
    
    with col_audit1:
        st.markdown('<div class="cockpit-card">', unsafe_allow_html=True)
        st.subheader("⚡ Execute Campaign")
        frame_count = st.number_input("Total Attack Frames", min_value=100, max_value=5000, value=1000, step=100)
        
        if st.button("🚀 Run Cyber Attack Campaign"):
            with st.spinner("Executing 1,000-frame attack simulation..."):
                audit_res = audit_report.run_attack_campaign(total_frames=frame_count)
                st.session_state.audit_res = audit_res
                st.success("✅ Campaign Complete!")

        if os.path.exists("kavach_security_audit.pdf"):
            st.markdown("<br/>", unsafe_allow_html=True)
            with open("kavach_security_audit.pdf", "rb") as pdf_file:
                st.download_button(
                    label="📄 Download Security Audit PDF",
                    data=pdf_file,
                    file_name="kavach_security_audit.pdf",
                    mime="application/pdf"
                )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_audit2:
        if os.path.exists("kavach_audit_results.json"):
            with open("kavach_audit_results.json", "r") as jf:
                res_data = json.load(jf)
                
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.markdown(f"""
                <div class="cockpit-card">
                    <div class="card-label">Total Frames</div>
                    <div class="card-value">{res_data.get('total_frames', 1000)}</div>
                </div>
                """, unsafe_allow_html=True)
            with mcol2:
                st.markdown(f"""
                <div class="cockpit-card">
                    <div class="card-label">Replays Defended</div>
                    <div class="card-value" style="color:#00FF66;">{res_data.get('replay_blocked', 150)}/150</div>
                </div>
                """, unsafe_allow_html=True)
            with mcol3:
                st.markdown(f"""
                <div class="cockpit-card">
                    <div class="card-label">Tampering Defended</div>
                    <div class="card-value" style="color:#00FF66;">{res_data.get('tamper_blocked', 100)}/100</div>
                </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br/>", unsafe_allow_html=True)
            st.json(res_data)

# -------------------------------------------------------------------------
# VIEW 3: LIVE 433 MHz RF WATERFALL
# -------------------------------------------------------------------------
elif app_mode == "📊 Live 433 MHz RF Waterfall":
    st.markdown("""
    <div class="hero-header">
        <div>
            <div class="hero-title">📊 433.92 MHz SDR Spectrum Analyzer</div>
            <div class="hero-subtitle">Real-Time Power Spectral Density & Waterfall Spectrogram</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    doppler_val = 0.0
    rssi_val = -75.0
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', 9999))
        s.sendall(b"POLL")
        data = s.recv(4096)
        s.close()
        
        if data and len(data) >= 6:
            payload = json.loads(data[6:].decode('utf-8'))
            doppler_val = payload.get("doppler_khz", 0.0)
            rssi_val = payload.get("rssi_dbm", -75.0)
    except Exception:
        pass

    st.session_state.rf_analyzer.update_spectrum(doppler_khz=doppler_val, rssi_dbm=rssi_val)
    fig_spec = st.session_state.rf_analyzer.generate_plotly_fig()
    st.plotly_chart(fig_spec, use_container_width=True)
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown("""
        <div class="cockpit-card">
            <div class="card-label">Center Frequency</div>
            <div class="card-value">433.92 <span class="card-unit">MHz</span></div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="cockpit-card">
            <div class="card-label">Doppler Shift</div>
            <div class="card-value">{doppler_val:+.2f} <span class="card-unit">kHz</span></div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown("""
        <div class="cockpit-card">
            <div class="card-label">Noise Floor</div>
            <div class="card-value">-110.0 <span class="card-unit">dBm</span></div>
        </div>
        """, unsafe_allow_html=True)

    time.sleep(1.0)
    st.rerun()

# -------------------------------------------------------------------------
# VIEW 4: REAL-TIME MISSION COCKPIT
# -------------------------------------------------------------------------
else:
    # Sidebar Command Controls
    st.sidebar.markdown("### 🕹️ Flight State Commands")
    col_c1, col_c2 = st.sidebar.columns(2)
    with col_c1:
        if st.button("NOMINAL"):
            st.session_state.cmd_trigger = b"CMD_STATE_NOMINAL"
        if st.button("ECLIPSE"):
            st.session_state.cmd_trigger = b"CMD_STATE_ECLIPSE"
    with col_c2:
        if st.button("SAFE MODE"):
            st.session_state.cmd_trigger = b"CMD_STATE_SAFE_MODE"
        if st.button("DETUMBLE"):
            st.session_state.cmd_trigger = b"CMD_STATE_DETUMBLE"

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚡ Cyber Pen-Test Vectors")
    if st.sidebar.button("💥 Trigger Replay Attack"):
        st.session_state.cmd_trigger = b"ATTACK_REPLAY"
    if st.sidebar.button("⚡ Trigger Bit-Flip Tamper"):
        st.session_state.cmd_trigger = b"ATTACK_TAMPER"

    # Socket Communication with Satellite Server
    telemetry = None
    server_status = False
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.8)
        s.connect(('127.0.0.1', 9999))
        server_status = True
        
        if st.session_state.cmd_trigger:
            s.sendall(st.session_state.cmd_trigger)
            st.session_state.cmd_trigger = None
        else:
            s.sendall(b"POLL")
            
        data = s.recv(4096)
        s.close()

        if data and len(data) >= 6:
            hdr_apid, hdr_seq, hdr_len = unpack_ccsds_header(data[:6])
            payload_str = data[6:].decode('utf-8')
            telemetry = json.loads(payload_str)
            telemetry["hdr_apid"] = hdr_apid
            telemetry["hdr_seq"] = hdr_seq
            st.session_state.last_telemetry = telemetry

            # Store ground track history
            st.session_state.history_lat.append(telemetry["lat"])
            st.session_state.history_lon.append(telemetry["lon"])
            if len(st.session_state.history_lat) > 120:
                st.session_state.history_lat.pop(0)
                st.session_state.history_lon.pop(0)
    except Exception:
        server_status = False
        telemetry = st.session_state.last_telemetry

    # Render Header Banner
    status_html = """
        <div class="status-badge-online">
            <div class="pulse-dot"></div> FLIGHT LINK ONLINE
        </div>
    """ if server_status else """
        <div class="status-badge-offline">
            🔴 SERVER DISCONNECTED
        </div>
    """

    st.markdown(f"""
    <div class="hero-header">
        <div>
            <div class="hero-title">🛰️ KAVACH Mission Control Cockpit</div>
            <div class="hero-subtitle">NIST FIPS 203 ML-KEM-768 • CCSDS 133.0-B SPACE PACKET ENGINE</div>
        </div>
        {status_html}
    </div>
    """, unsafe_allow_html=True)

    if telemetry:
        # Top Metrics Grid (5 Cards)
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            state_color = "#00FF66" if telemetry.get('mode') == "NOMINAL" else "#FFD700" if telemetry.get('mode') == "ECLIPSE" else "#FF4B4B"
            st.markdown(f"""
            <div class="cockpit-card">
                <div class="card-label">Flight Mode</div>
                <div class="card-value" style="color:{state_color};">{telemetry.get('mode', 'NOMINAL')}</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="cockpit-card">
                <div class="card-label">CCSDS Sequence</div>
                <div class="card-value">#{telemetry.get('hdr_seq', 0)}</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="cockpit-card">
                <div class="card-label">Bus Battery</div>
                <div class="card-value">{telemetry.get('battery', 98.5):.1f}<span class="card-unit">%</span></div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="cockpit-card">
                <div class="card-label">Doppler Shift</div>
                <div class="card-value">{telemetry.get('doppler_khz', 0.0):+.2f}<span class="card-unit">kHz</span></div>
            </div>
            """, unsafe_allow_html=True)
        with m5:
            st.markdown(f"""
            <div class="cockpit-card">
                <div class="card-label">Signal RSSI</div>
                <div class="card-value">{telemetry.get('rssi_dbm', -75.0):.1f}<span class="card-unit">dBm</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Main Layout: Earth Orbit Tracking Map (Left 65%) + Security Telemetry Log (Right 35%)
        col_map, col_info = st.columns([2, 1])

        with col_map:
            st.markdown("<div class='card-label' style='margin-bottom:8px;'>📡 3D Orbit Ground Track & Ground Station Pass</div>", unsafe_allow_html=True)
            
            fig_map = go.Figure()

            # Orbit Trail Path
            fig_map.add_trace(go.Scattergeo(
                lat=st.session_state.history_lat,
                lon=st.session_state.history_lon,
                mode='lines',
                line=dict(width=2.5, color='#00F0FF'),
                name='Orbit Ground Track'
            ))

            # Satellite Marker
            fig_map.add_trace(go.Scattergeo(
                lat=[telemetry["lat"]],
                lon=[telemetry["lon"]],
                mode='markers+text',
                marker=dict(size=14, color='#00FF66', symbol='diamond', line=dict(width=1, color='#FFFFFF')),
                text=["  KAVACH Satellite"],
                textposition="middle right",
                name='Satellite Position'
            ))

            # ISTRAC Ground Station Marker
            fig_map.add_trace(go.Scattergeo(
                lat=[12.9716],
                lon=[77.5946],
                mode='markers+text',
                marker=dict(size=12, color='#FFD700', symbol='square'),
                text=["  ISTRAC Bengaluru"],
                textposition="bottom center",
                name='ISTRAC Bengaluru'
            ))

            fig_map.update_geos(
                projection_type="orthographic",
                showcoastlines=True, coastlinecolor="#1b2e4b",
                showland=True, landcolor="#0a1424",
                showocean=True, oceancolor="#040811",
                showlakes=True, lakecolor="#040811",
                showcountries=True, countrycolor="#1b2e4b"
            )

            fig_map.update_layout(
                template='plotly_dark',
                paper_bgcolor='#04070d',
                plot_bgcolor='#04070d',
                height=480,
                margin=dict(l=0, r=0, t=0, b=0),
                showlegend=False
            )

            st.plotly_chart(fig_map, use_container_width=True)

        with col_info:
            st.markdown("<div class='card-label' style='margin-bottom:8px;'>🔒 Cryptographic Security Telemetry</div>", unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="cockpit-card" style="margin-bottom:12px;">
                <div class="card-label">Handshake KEM Algorithm</div>
                <div style="font-family:'IBM Plex Mono'; font-size:14px; color:#00FF66; font-weight:700;">NIST FIPS 203 ML-KEM-768</div>
                <div style="font-size:11px; color:#7d8ea3; margin-top:4px;">Module-Lattice Key Encapsulation (Level 3)</div>
            </div>

            <div class="cockpit-card" style="margin-bottom:12px;">
                <div class="card-label">Session Key KDF</div>
                <div style="font-family:'IBM Plex Mono'; font-size:14px; color:#00F0FF; font-weight:700;">NIST SP 800-56C HKDF-SHA256</div>
                <div style="font-size:11px; color:#7d8ea3; margin-top:4px;">Derived Keys: K_enc (32B) + K_mac (32B)</div>
            </div>

            <div class="cockpit-card" style="margin-bottom:12px;">
                <div class="card-label">Payload Cipher Suite</div>
                <div style="font-family:'IBM Plex Mono'; font-size:14px; color:#ffffff; font-weight:700;">AES-256-GCM AEAD</div>
                <div style="font-size:11px; color:#7d8ea3; margin-top:4px;">12-Byte Nonce + 16-Byte Auth Tag</div>
            </div>

            <div class="cockpit-card">
                <div class="card-label">Anti-Replay Window Engine</div>
                <div style="font-family:'IBM Plex Mono'; font-size:14px; color:#00FF66; font-weight:700;">64-Frame Sliding Bitmap</div>
                <div style="font-size:11px; color:#7d8ea3; margin-top:4px;">100% Duplicate Sequence Suppression</div>
            </div>
            """, unsafe_allow_html=True)

        # Tab Section
        tab1, tab2 = st.tabs(["📜 CCSDS 133.0-B Primary Header Inspector", "⚡ Space Physical Link Budget"])
        
        with tab1:
            st.json({
                "CCSDS_Version": 0,
                "Packet_Type": "0 (Telemetry)" if telemetry.get("hdr_apid") == 0x100 else "1 (Telecommand)",
                "APID": hex(telemetry.get("hdr_apid", 0x100)),
                "Sequence_Count": telemetry.get("hdr_seq"),
                "Payload_Length_Bytes": 128,
                "Crypto_Protection": "ACTIVE (AES-256-GCM AEAD)"
            })
            
        with tab2:
            rf_m = calculate_rf_metrics(telemetry.get("alt", 500.0), telemetry.get("lat"), telemetry.get("lon"))
            st.json(rf_m)

    else:
        st.warning("⚠️ Waiting for telemetry connection from Satellite server on port 9999...")
        st.info("💡 Run `python satellite.py` in another terminal!")

    time.sleep(1.2)
    st.rerun()
