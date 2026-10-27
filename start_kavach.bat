@echo off
title KAVACH Master Launcher
echo ====================================================
echo  BOOTING KAVACH POST-QUANTUM MISSION CONTROL
echo ====================================================
echo.
echo [1/2] Launching Spacecraft Flight Software (satellite.py)...
start "KAVACH Satellite Server" cmd /k "python satellite.py"
timeout /t 2 /nobreak > nul
echo [2/2] Launching Mission Control Dashboard (dashboard.py)...
start "KAVACH Mission Control" cmd /k "python -m streamlit run dashboard.py"
echo.
echo ====================================================
echo  ALL SYSTEMS ONLINE! 
echo  Dashboard opening in browser at http://localhost:8501
echo ====================================================
