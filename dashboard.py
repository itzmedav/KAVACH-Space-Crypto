import streamlit as st
import plotly.graph_objects as go
import socket
import json
import time
import pandas as pd
from ccsds import derive_session_keys, pack_ccsds_header, unpack_ccsds_header
from rf_channel import corrupt_payload
from oqs import KeyEncapsulation
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

st.set_page_config(
    page_title="KAVACH Mission Control",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Minimal Aerospace Theme ──────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }
    .stApp {
        background: #070b12;
        color: #c8d0dc;
    }
    /* Hide Streamlit chrome */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 1rem;
        max-width: 1400px;
    }
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0a0f18;
        border-right: 1px solid #1a2332;
    }
    section[data-testid="stSidebar"] .stMarkdown {
        color: #8b9bb4;
    }
    /* Metric cards */
    .k-card {
        background: #0d1520;
        border: 1px solid #1a2332;
        border-radius: 6px;
        padding: 14px 16px;
        height: 100%;
    }
    .k-label {
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #5a6a82;
        margin-bottom: 6px;
        font-weight: 500;
    }
    .k-value {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.45rem;
        font-weight: 500;
        color: #e8eef7;
        line-height: 1.2;
    }
    .k-unit {
        font-size: 0.75rem;
        color: #5a6a82;
        margin-left: 4px;
    }
    /* Status pills */
    .pill {
        display: inline-block;
        font-size: 0.72rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        padding: 3px 10px;
        border-radius: 3px;
        font-family: 'IBM Plex Mono', monospace;
    }
    .pill-ok   { background: #0d2818; color: #3dd68c; border: 1px solid #1a4d32; }
    .pill-safe { background: #2a1f08; color: #f0a500; border: 1px solid #5c4200; }
    .pill-pqc  { background: #0a1f2a; color: #00d4aa; border: 1px solid #0d4a3e; }
    .pill-alert{ background: #2a0f0f; color: #ff6b6b; border: 1px solid #5c1a1a; }
    /* Section headers */
    .sec {
        font-size: 0.72rem;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #5a6a82;
        font-weight: 600;
        margin: 18px 0 10px 0;
        border-bottom: 1px solid #1a2332;
        padding-bottom: 6px;
    }
    /* Buttons in sidebar */
    .stButton > button {
        width: 100%;
        border-radius: 4px;
        font-size: 0.8rem;
        font-weight: 500;
        border: 1px solid #1a2332;
        background: #0d1520;
        color: #c8d0dc;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #00d4aa;
        color: #00d4aa;
        background: #0a1a18;
    }
    /* Dataframe */
    .stDataFrame { border: 1px solid #1a2332; border-radius: 4px; }
    /* JSON */
    .stJson { background: #0d1520 !important; border: 1px solid #1a2332; border-radius: 4px; }
    /* Dividers */
    hr { border-color: #1a2332 !important; margin: 0.8rem 0; }
</style>
""", unsafe_allow_html=True)

# ── Session State ────────────────────────────────────────────────────────
for key, default in [
    ("history", []), ("seq_count", 1),
    ("replays_blocked", 0), ("tampered_blocked", 0),
    ("cmd_logs", [])
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Sidebar ──────────────────────────────────────────────────────────────
st.sidebar.markdown("## KAVACH")
st.sidebar.caption("Post-Quantum LEO Link")
st.sidebar.markdown("---")

st.sidebar.markdown('<div class="sec">Telecommand</div>', unsafe_allow_html=True)
c1, c2 = st.sidebar.columns(2)
cmd_safe = c1.button("SAFE MODE")
cmd_nom  = c2.button("NOMINAL")
c3, c4 = st.sidebar.columns(2)
cmd_ecl  = c3.button("ECLIPSE")
cmd_det  = c4.button("DETUMBLE")

st.sidebar.markdown('<div class="sec">Pen-Test</div>', unsafe_allow_html=True)
inject_replay = st.sidebar.button("REPLAY ATTACK")
inject_tamper = st.sidebar.button("BIT-FLIP TAMPER")

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="font-size:0.7rem;color:#5a6a82;line-height:1.6;">
ML-KEM-768 · HKDF-SHA256<br>
AES-256-GCM · CCSDS 133.0-B<br>
64-Frame Anti-Replay
</div>
""", unsafe_allow_html=True)

# ── Socket Dispatch ──────────────────────────────────────────────────────
def dispatch(command_str=None, attack_mode=None):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", 9999))

        raw_pk = s.recv(2048)
        if not raw_pk:
            s.close()
            return None, None

        with KeyEncapsulation("Kyber768") as kem:
            ct, ss = kem.encap_secret(raw_pk)
        s.sendall(ct)
        k_enc, _ = derive_session_keys(ss)

        frame = s.recv(4096)
        hdr, payload = unpack_ccsds_header(frame)

        aesgcm = AESGCM(k_enc)
        nonce, ct_tag = payload[:12], payload[12:]
        try:
            pt = aesgcm.decrypt(nonce, ct_tag, frame[:6])
            telemetry = json.loads(pt.decode())
        except Exception as e:
            telemetry = {"error": str(e)}

        if command_str:
            body = json.dumps({"cmd": command_str, "ts": time.time()}).encode()
            seq = st.session_state.seq_count
            st.session_state.seq_count += 1
            h = pack_ccsds_header(0x200, seq, len(body), packet_type=1)
            n = bytes([seq % 256] * 12)
            s.sendall(h + n + aesgcm.encrypt(n, body, h))
            st.session_state.cmd_logs.append(
                {"seq": seq, "cmd": command_str, "status": "OK"}
            )
        elif attack_mode == "replay":
            h = pack_ccsds_header(0x200, max(0, st.session_state.seq_count - 1), 6)
            s.sendall(h + payload)
            st.session_state.replays_blocked += 1
        elif attack_mode == "tamper":
            bad = corrupt_payload(payload)
            h = pack_ccsds_header(0x200, st.session_state.seq_count, len(bad))
            s.sendall(h + bad)
            st.session_state.tampered_blocked += 1
            st.session_state.seq_count += 1

        s.close()
        return telemetry, hdr
    except Exception:
        return None, None

pending = None
if cmd_safe: pending = "CMD_SAFE_MODE"
elif cmd_nom: pending = "CMD_NOMINAL"
elif cmd_ecl: pending = "CMD_ECLIPSE"
elif cmd_det: pending = "CMD_DETUMBLE"
attack = "replay" if inject_replay else ("tamper" if inject_tamper else None)

telemetry, hdr = dispatch(command_str=pending, attack_mode=attack)

# ── Header Bar ───────────────────────────────────────────────────────────
mode = telemetry.get("mode", "—") if telemetry else "—"
pill_cls = "pill-ok" if mode == "NOMINAL" else "pill-safe"

h1, h2, h3, h4, h5 = st.columns([2.2, 1.2, 1.2, 1.2, 1.4])
with h1:
    st.markdown(f"""
    <div class="k-card">
      <div class="k-label">Flight Mode</div>
      <span class="pill {pill_cls}">{mode}</span>
      &nbsp;<span class="pill pill-pqc">ML-KEM-768</span>
    </div>
    """, unsafe_allow_html=True)
with h2:
    st.markdown(f"""
    <div class="k-card">
      <div class="k-label">Replays Blocked</div>
      <div class="k-value" style="color:#ff6b6b;">{st.session_state.replays_blocked}</div>
    </div>
    """, unsafe_allow_html=True)
with h3:
    st.markdown(f"""
    <div class="k-card">
      <div class="k-label">Tamper Rejected</div>
      <div class="k-value" style="color:#f0a500;">{st.session_state.tampered_blocked}</div>
    </div>
    """, unsafe_allow_html=True)
with h4:
    ecl = telemetry.get("eclipse", False) if telemetry else False
    st.markdown(f"""
    <div class="k-card">
      <div class="k-label">Eclipse</div>
      <div class="k-value" style="font-size:1.1rem;">{'YES' if ecl else 'NO'}</div>
    </div>
    """, unsafe_allow_html=True)
with h5:
    st.markdown(f"""
    <div class="k-card">
      <div class="k-label">Link</div>
      <span class="pill pill-ok">ENCRYPTED</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("")  # spacer

# ── Main Content ─────────────────────────────────────────────────────────
if telemetry and "error" not in telemetry:
    st.session_state.history.append(telemetry)
    if len(st.session_state.history) > 40:
        st.session_state.history.pop(0)
    df = pd.DataFrame(st.session_state.history)

    left, right = st.columns([5.5, 4.5], gap="medium")

    # ── Ground Track ──
    with left:
        st.markdown('<div class="sec">Ground Track · ISTRAC Bengaluru</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scattergeo(
            lat=[12.9716], lon=[77.5946],
            mode="markers+text", text=["ISTRAC"],
            textposition="top center",
            textfont=dict(size=10, color="#00d4aa", family="IBM Plex Mono"),
            marker=dict(size=11, color="#00d4aa", symbol="triangle-up"),
            name="GS", hoverinfo="skip"
        ))
        if "lat" in df.columns and len(df) > 0:
            fig.add_trace(go.Scattergeo(
                lat=df["lat"], lon=df["lon"],
                mode="lines",
                line=dict(width=1.5, color="#3b82f6"),
                name="Track", hoverinfo="skip"
            ))
            fig.add_trace(go.Scattergeo(
                lat=[df["lat"].iloc[-1]], lon=[df["lon"].iloc[-1]],
                mode="markers",
                marker=dict(size=9, color="#ff6b6b", symbol="circle"),
                name="SAT", hoverinfo="skip"
            ))
        fig.update_layout(
            geo=dict(
                projection_type="orthographic",
                projection_rotation=dict(
                    lon=float(df["lon"].iloc[-1]) if "lon" in df.columns and len(df) else 78,
                    lat=float(df["lat"].iloc[-1]) if "lat" in df.columns and len(df) else 13
                ),
                showland=True, landcolor="#111827",
                showocean=True, oceancolor="#070b12",
                showcountries=True, countrycolor="#1e293b",
                showcoastlines=True, coastlinecolor="#1e293b",
                bgcolor="rgba(0,0,0,0)",
                lonaxis=dict(showgrid=True, gridcolor="#1a2332", gridwidth=0.5),
                lataxis=dict(showgrid=True, gridcolor="#1a2332", gridwidth=0.5),
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            height=360,
            showlegend=False
        )
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    # ── Telemetry Strip ──
    with right:
        st.markdown('<div class="sec">Orbital State</div>', unsafe_allow_html=True)
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Altitude</div>
              <div class="k-value">{telemetry.get('alt_km',0):.1f}<span class="k-unit">km</span></div>
            </div>
            """, unsafe_allow_html=True)
        with r1c2:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Velocity</div>
              <div class="k-value">{telemetry.get('vel_kms',0):.2f}<span class="k-unit">km/s</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Battery</div>
              <div class="k-value">{telemetry.get('battery_v',0):.2f}<span class="k-unit">V</span></div>
            </div>
            """, unsafe_allow_html=True)
        with r2c2:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Solar</div>
              <div class="k-value">{telemetry.get('solar_w',0):.1f}<span class="k-unit">W</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        r3c1, r3c2 = st.columns(2)
        with r3c1:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Angular Rate</div>
              <div class="k-value">{telemetry.get('ang_vel',0):.2f}<span class="k-unit">°/s</span></div>
            </div>
            """, unsafe_allow_html=True)
        with r3c2:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Temp</div>
              <div class="k-value">{telemetry.get('temp_c',0):.1f}<span class="k-unit">°C</span></div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("")
        r4c1, r4c2 = st.columns(2)
        with r4c1:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">Doppler</div>
              <div class="k-value">{telemetry.get('doppler_hz',0):.0f}<span class="k-unit">Hz</span></div>
            </div>
            """, unsafe_allow_html=True)
        with r4c2:
            st.markdown(f"""
            <div class="k-card">
              <div class="k-label">RSSI / SNR</div>
              <div class="k-value" style="font-size:1.1rem;">{telemetry.get('rssi_dbm',0):.0f}<span class="k-unit">dBm</span>
              &nbsp;{telemetry.get('snr_db',0):.0f}<span class="k-unit">dB</span></div>
            </div>
            """, unsafe_allow_html=True)

    # ── Trends ──
    st.markdown('<div class="sec">Bus Trends</div>', unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)

    def mini_chart(y, title, color):
        f = go.Figure()
        f.add_trace(go.Scatter(
            y=y, mode="lines",
            line=dict(width=1.5, color=color),
            fill="tozeroy", fillcolor=color.replace(")", ",0.08)").replace("rgb", "rgba") if False else "rgba(0,212,170,0.06)"
        ))
        f.update_layout(
            title=dict(text=title, font=dict(size=11, color="#5a6a82", family="IBM Plex Sans")),
            margin=dict(l=0, r=0, t=28, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=160,
            xaxis=dict(visible=False),
            yaxis=dict(gridcolor="#1a2332", tickfont=dict(size=9, color="#5a6a82"), zeroline=False),
            showlegend=False
        )
        return f

    with t1:
        if "battery_v" in df.columns:
            st.plotly_chart(mini_chart(df["battery_v"], "BATTERY (V)", "#3dd68c"), width="stretch", config={"displayModeBar": False})
    with t2:
        if "solar_w" in df.columns:
            st.plotly_chart(mini_chart(df["solar_w"], "SOLAR (W)", "#f0a500"), width="stretch", config={"displayModeBar": False})
    with t3:
        if "ang_vel" in df.columns:
            st.plotly_chart(mini_chart(df["ang_vel"], "ANGULAR RATE (°/s)", "#3b82f6"), width="stretch", config={"displayModeBar": False})

    # ── Bottom: Header + Logs ──
    st.markdown('<div class="sec">CCSDS Frame · Command Log</div>', unsafe_allow_html=True)
    b1, b2 = st.columns([1, 1], gap="medium")
    with b1:
        if hdr:
            st.json({
                "APID": f"0x{hdr['apid']:03X}",
                "Type": "TM" if hdr["type"] == 0 else "TC",
                "Seq": hdr["seq"],
                "Len": hdr["len"],
                "Ver": hdr["version"]
            })
    with b2:
        if st.session_state.cmd_logs:
            st.dataframe(
                pd.DataFrame(st.session_state.cmd_logs).tail(6),
                width="stretch",
                hide_index=True
            )
        else:
            st.caption("No telecommands yet.")

else:
    st.markdown("""
    <div class="k-card" style="text-align:center;padding:40px;">
      <div class="k-label">Link Status</div>
      <div class="k-value" style="font-size:1rem;color:#5a6a82;">Connecting to spacecraft · TCP 9999</div>
    </div>
    """, unsafe_allow_html=True)

time.sleep(1.5)
st.rerun()
