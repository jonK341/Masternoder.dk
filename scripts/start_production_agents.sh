#!/bin/bash
# Start Production Agents
# Runs agents directly in production environment

cd /var/www/html/vidgenerator
python3 scripts/production_agent_runner.py >> logs/agents/production_runner.log 2>&1 &

echo $! > logs/agents/production_runner.pid
echo "Production agents started (PID: $(cat logs/agents/production_runner.pid))"
