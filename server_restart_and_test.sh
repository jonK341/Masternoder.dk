#!/bin/bash
# Server-side script to restart services and test
# Run this ON THE SERVER: cd

echo "============================================================"
echo "RESTART ALL SERVICES AND TEST"
echo "============================================================"
echo ""

# Step 1: Clear cache
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
    systemctl status uwsgi --no-pager -l | head -5
else
    echo "[WARN] uWSGI may not be running"
    systemctl status uwsgi --no-pager -l | head -10
fi
echo ""

# Step 3: Restart Python Proxy
echo "[STEP 3] Restarting python-proxy..."
sudo systemctl restart python-proxy
sleep 3
if systemctl is-active --quiet python-proxy; then
    echo "[OK] python-proxy is running"
    systemctl status python-proxy --no-pager -l | head -5
else
    echo "[WARN] python-proxy may not be running"
    systemctl status python-proxy --no-pager -l | head -10
fi
echo ""

# Step 4: Restart Apache
echo "[STEP 4] Restarting Apache..."
sudo systemctl restart apache2
sleep 2
if systemctl is-active --quiet apache2; then
    echo "[OK] Apache is running"
else
    echo "[WARN] Apache may not be running"
fi
echo ""

# Step 5: Wait for initialization
echo "[STEP 5] Waiting for services to initialize..."
sleep 5
echo "[OK] Ready for testing"
echo ""

# Step 6: Test endpoints
echo "============================================================"
echo "TESTING ENDPOINTS"
echo "============================================================"
echo ""

BASE_URL="https://masternoder.dk"
TEST_USER="test_user"

test_endpoint() {
    local endpoint=$1
    local description=$2
    echo "[TEST] $description"
    echo "URL: ${BASE_URL}${endpoint}"
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" "${BASE_URL}${endpoint}")
    http_code=$(echo "$response" | grep "HTTP_CODE" | cut -d: -f2)
    body=$(echo "$response" | sed '/HTTP_CODE/d')
    
    if [ "$http_code" = "200" ]; then
        echo "[OK] Status: $http_code"
        echo "Response: $(echo "$body" | head -3)"
    else
        echo "[FAIL] Status: $http_code"
        echo "Response: $(echo "$body" | head -3)"
    fi
    echo ""
}

test_endpoint "/vidgenerator/api/ultra-resource/energy?user_id=${TEST_USER}" "Ultra Resource Controller - Energy"
test_endpoint "/vidgenerator/api/game-mechanics/subjects?user_id=${TEST_USER}" "Game Mechanics - Subjects"
test_endpoint "/vidgenerator/api/skill-reward/completions?user_id=${TEST_USER}" "Skill Rewards - Completions"
test_endpoint "/vidgenerator/api/calendar/events?user_id=${TEST_USER}" "Calendar Planner - Events"
test_endpoint "/vidgenerator/api/todos/list?user_id=${TEST_USER}" "Todos - List"
test_endpoint "/vidgenerator/api/decision-trees/tech?user_id=${TEST_USER}" "Decision Trees - Tech"
test_endpoint "/vidgenerator/api/groups/user?user_id=${TEST_USER}" "Groups - User Groups"
test_endpoint "/vidgenerator/api/scanner/efficiency?user_id=${TEST_USER}" "Cognitive Scanner - Efficiency"
test_endpoint "/vidgenerator/api/skills/abilities" "Enhanced Skills - Abilities"
test_endpoint "/vidgenerator/api/points/json/get?user_id=${TEST_USER}" "Points JSON - Get Points"

echo "============================================================"
echo "TESTING COMPLETE"
echo "============================================================"
echo ""
echo "[INFO] Check results above"
echo "[INFO] Status 200 = Working"
echo "[INFO] Status 404 = Route not found (files may not be deployed)"
echo ""

