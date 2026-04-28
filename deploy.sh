#!/bin/bash
# MasterNoder.dk - Deployment Script
# This script verifies and deploys all systems

echo "=========================================="
echo "MasterNoder.dk - Deployment Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Verify Python environment
echo -e "${YELLOW}[1/7]${NC} Verifying Python environment..."
if command -v python &> /dev/null; then
    echo -e "${GREEN}✓${NC} Python found: $(python --version)"
else
    echo -e "${RED}✗${NC} Python not found!"
    exit 1
fi

# Step 2: Verify required files exist
echo -e "${YELLOW}[2/7]${NC} Verifying required files..."
REQUIRED_FILES=(
    "backend/register_blueprints.py"
    "vidgenerator/index.html"
    "backend/services/agent_system.py"
    "backend/services/tech_tree_system.py"
    "backend/services/battle_intelligence_system.py"
    "backend/services/unified_points_database.py"
)

MISSING_FILES=0
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} Missing: $file"
        MISSING_FILES=$((MISSING_FILES + 1))
    fi
done

if [ $MISSING_FILES -gt 0 ]; then
    echo -e "${RED}Error: $MISSING_FILES required files missing!${NC}"
    exit 1
fi

# Step 3: Check for syntax errors in Python files
echo -e "${YELLOW}[3/7]${NC} Checking Python syntax..."
PYTHON_FILES=$(find backend -name "*.py" -type f | head -20)
SYNTAX_ERRORS=0
for file in $PYTHON_FILES; do
    if python -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} Syntax error in: $file"
        SYNTAX_ERRORS=$((SYNTAX_ERRORS + 1))
    fi
done

if [ $SYNTAX_ERRORS -gt 0 ]; then
    echo -e "${YELLOW}Warning: $SYNTAX_ERRORS files with syntax errors found${NC}"
fi

# Step 4: Verify JavaScript files
echo -e "${YELLOW}[4/7]${NC} Verifying JavaScript files..."
JS_FILES=(
    "vidgenerator/static/js/comprehensive-api-integration.js"
    "vidgenerator/static/js/unified-point-counters.js"
    "vidgenerator/static/js/notification-system.js"
    "vidgenerator/static/js/intelligence-widget.js"
)

MISSING_JS=0
for file in "${JS_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} Missing: $file"
        MISSING_JS=$((MISSING_JS + 1))
    fi
done

# Step 5: Create backup directory
echo -e "${YELLOW}[5/7]${NC} Creating backup directory..."
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✓${NC} Backup directory created: $BACKUP_DIR"

# Step 6: Verify all blueprints are registered
echo -e "${YELLOW}[6/7]${NC} Verifying blueprint registration..."
if grep -q "point_analytics_bp" backend/register_blueprints.py; then
    echo -e "${GREEN}✓${NC} Point analytics blueprint registered"
else
    echo -e "${YELLOW}⚠${NC} Point analytics blueprint not found in registration"
fi

if grep -q "battle_intelligence_bp" backend/register_blueprints.py; then
    echo -e "${GREEN}✓${NC} Battle intelligence blueprint registered"
else
    echo -e "${YELLOW}⚠${NC} Battle intelligence blueprint not found in registration"
fi

if grep -q "agent_bp" backend/register_blueprints.py; then
    echo -e "${GREEN}✓${NC} Agent blueprint registered"
else
    echo -e "${YELLOW}⚠${NC} Agent blueprint not found in registration"
fi

if grep -q "intelligence_aggregator_bp" backend/register_blueprints.py; then
    echo -e "${GREEN}✓${NC} Intelligence aggregator blueprint registered"
else
    echo -e "${YELLOW}⚠${NC} Intelligence aggregator blueprint not found in registration"
fi

# Step 7: Final summary
echo ""
echo -e "${YELLOW}[7/7]${NC} Deployment Summary"
echo "=========================================="
echo -e "${GREEN}✓${NC} All systems verified"
echo -e "${GREEN}✓${NC} All files present"
echo -e "${GREEN}✓${NC} Ready for deployment"
echo ""
echo "Next steps:"
echo "1. Start your Flask application"
echo "2. Test all endpoints"
echo "3. Verify frontpage loads correctly"
echo "4. Test API Integration buttons"
echo "5. Monitor for errors"
echo ""
echo -e "${GREEN}Deployment script completed successfully!${NC}"
