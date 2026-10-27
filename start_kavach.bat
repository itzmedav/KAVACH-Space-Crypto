@echo off
title KAVACH - Post-Quantum Space System Launcher
echo ==========================================================
echo [KAVACH] Post-Quantum Space Communication Protocol
echo ==========================================================
echo.

echo [1/2] Launching Satellite Flight Software Server...
start "KAVACH Satellite Server" cmd /k "python satellite.py"

echo [2/2] Launching Mission Control Cockpit (Streamlit)...
start "KAVACH Mission Control" cmd /k "python -m streamlit run dashboard.py"

echo.
echo ==========================================================
echo [SUCCESS] KAVACH System started.
echo Browser opening automatically at http://localhost:8501
echo ==========================================================
pause
