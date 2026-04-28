@echo off
REM Start Production Agents on Windows
cd /d %~dp0..
start /B python scripts/production_agent_runner.py
echo Production agents started in background
