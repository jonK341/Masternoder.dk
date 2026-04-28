#!/bin/bash
# Restart All Services and Test Endpoints
# Run this on the server: bash restart_services_and_test.sh

echo "============================================================"
echo "RESTARTING ALL SERVICES AND TESTING"
echo "============================================================"
echo ""

# Step 1: Clear Python cache
echo "[STEP 1] Clearing Python cache..."
find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find /var/www/html -type f -name "*.pyc" -delete 2>/dev/null || true
echo "[OK] Cache cleared"
echo ""

# Step 2: Restart uWSGI
echo "[STEP 2] Restarting uWSGI..."
sudo systemctl restart uwsgi
sleep 3
if systemctl is-active --quiet uwsgi; then
    echo "[OK] uWSGI is running"
else
    echo "[WARN] uWSGI status unclear"
fi
echo ""

# Step 3: Restart Python Proxy
echo "[STEP 3] Restarting python-proxy..."
sudo systemctl restart python-proxy
sleep 3
if systemctl is-active --quiet python-proxy; then
    echo "[OK] python-proxy is running"
else
    echo "[WARN] python-proxy status unclear"
fi
echo ""

# Step 4: Restart Apache (optional)
echo "[STEP 4] Restarting Apache..."
sudo systemctl restart apache2
sleep 2
if systemctl is-active --quiet apache2; then
    echo "[OK] Apache is running"
else
    echo "[WARN] Apache status unclear"
fi
echo ""

# Step 5: Wait for services to fully start
echo "[STEP 5] Waiting for services to initialize..."
sleep 5
echo "[OK] Services should be ready"
echo ""

# Step 6: Test endpoints
echo "============================================================"
echo "TESTING ENDPOINTS"
echo "============================================================"
echo ""

BASE_URL="https://masternoder.dk"
TEST_USER="test_user"

# Test Ultra Resource Controller
echo "[TEST 1] Ultra Resource Controller - Energy Status"
curl -s "${BASE_URL}/vidgenerator/api/ultra-resource/energy?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Game Mechanics
echo "[TEST 2] Game Mechanics - Subjects"
curl -s "${BASE_URL}/vidgenerator/api/game-mechanics/subjects?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Skill Rewards
echo "[TEST 3] Skill Rewards - Completions"
curl -s "${BASE_URL}/vidgenerator/api/skill-reward/completions?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Calendar Planner
echo "[TEST 4] Calendar Planner - Events"
curl -s "${BASE_URL}/vidgenerator/api/calendar/events?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Todos
echo "[TEST 5] Todos - List"
curl -s "${BASE_URL}/vidgenerator/api/todos/list?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Decision Trees
echo "[TEST 6] Decision Trees - Tech Tree"
curl -s "${BASE_URL}/vidgenerator/api/decision-trees/tech?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Groups
echo "[TEST 7] Groups - User Groups"
curl -s "${BASE_URL}/vidgenerator/api/groups/user?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Cognitive Scanner
echo "[TEST 8] Cognitive Scanner - Efficiency"
curl -s "${BASE_URL}/vidgenerator/api/scanner/efficiency?user_id=${TEST_USER}" | head -20
echo ""
echo ""

# Test Enhanced Systems
echo "[TEST 9] Enhanced Systems - Skills Abilities"
curl -s "${BASE_URL}/vidgenerator/api/skills/abilities" | head -20
echo ""
echo ""

# Test Points JSON
echo "[TEST 10] Points JSON - Get Points"
curl -s "${BASE_URL}/vidgenerator/api/points/json/get?user_id=${TEST_USER}" | head -20
echo ""
echo ""

echo "============================================================"
echo "TESTING COMPLETE"
echo "============================================================"
echo ""
echo "[INFO] Check output above for any errors"
echo "[INFO] All endpoints should return JSON responses"
echo ""

