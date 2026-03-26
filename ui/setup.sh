#!/bin/bash

# Setup script for HVAC-LLM UI
echo "=================================="
echo "HVAC-LLM UI Setup Script"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Install Backend Dependencies
echo -e "${GREEN}Installing Backend Dependencies...${NC}"

# Check if venv exists, if not notify user
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Warning: No .venv directory found${NC}"
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

.venv/bin/pip install Flask>=2.3.0 flask-cors>=4.0.0 flask-socketio>=5.3.0 werkzeug>=2.3.0 python-socketio>=5.9.0 eventlet>=0.33.0 python-engineio>=4.7.0

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠ Some backend dependencies may have failed to install${NC}"
fi

echo ""

# Install Frontend Dependencies
echo -e "${GREEN}Installing Frontend Dependencies...${NC}"
cd ui/frontend

if [ ! -f "package.json" ]; then
    echo "Error: package.json not found in ui/frontend"
    exit 1
fi

npm install

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo "Error: Failed to install frontend dependencies"
    exit 1
fi

cd ../..

echo ""
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo ""
echo "To start the UI, run:"
echo "  ./ui/start.sh"
echo ""
