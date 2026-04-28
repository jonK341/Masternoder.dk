#!/bin/bash
# Server-side fix script for line 528
# Run this directly on the Ubuntu server

REMOTE_PATH="/var/www/html/vidgenerator"
FILE_PATH="${REMOTE_PATH}/src/web/routes/__init__.py"

echo "============================================================"
echo "SERVER-SIDE FIX FOR LINE 528"
echo "============================================================"

# Step 1: Stop uWSGI
echo ""
echo "1. Stopping uWSGI..."
systemctl stop uwsgi
sleep 2

# Step 2: Set permissions
echo ""
echo "2. Setting file permissions..."
chmod 666 "$FILE_PATH"
chown www-data:www-data "$FILE_PATH"

# Step 3: Clear all caches
echo ""
echo "3. Clearing all Python caches..."
find "$REMOTE_PATH" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null
find "$REMOTE_PATH" -name '*.pyc' -delete 2>/dev/null
find "$REMOTE_PATH" -name '*.pyo' -delete 2>/dev/null
rm -rf "${REMOTE_PATH}/src/web/routes/__pycache__" 2>/dev/null
rm -rf "${REMOTE_PATH}/src/web/__pycache__" 2>/dev/null
rm -rf "${REMOTE_PATH}/src/__pycache__" 2>/dev/null

# Step 4: Verify syntax
echo ""
echo "4. Verifying syntax..."
python3 -m py_compile "$FILE_PATH" 2>&1
if [ $? -eq 0 ]; then
    echo "   ✅ Syntax is valid"
else
    echo "   ❌ Syntax error found"
    exit 1
fi

# Step 5: Test import
echo ""
echo "5. Testing import..."
cd "$REMOTE_PATH"
python3 -B -c "import sys; sys.path.insert(0, '$REMOTE_PATH'); import src.web.routes; print('✅ Import successful')" 2>&1

# Step 6: Test application creation
echo ""
echo "6. Testing application creation..."
python3 -B -c "import sys; sys.path.insert(0, '$REMOTE_PATH'); from src.app import create_app; app = create_app(); print('✅ Application creation successful')" 2>&1

# Step 7: Restore permissions
echo ""
echo "7. Restoring file permissions..."
chmod 644 "$FILE_PATH"
chown www-data:www-data "$FILE_PATH"

# Step 8: Start uWSGI
echo ""
echo "8. Starting uWSGI..."
systemctl start uwsgi
sleep 5

# Step 9: Check status
echo ""
echo "9. Checking uWSGI status..."
systemctl status uwsgi --no-pager -l | head -20

echo ""
echo "============================================================"
echo "✅ FIX COMPLETE"
echo "============================================================"

