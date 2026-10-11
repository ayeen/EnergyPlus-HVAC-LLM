#!/bin/bash

# Simple HVAC-LLM UI Startup Script
echo "🚀 Starting HVAC-LLM Interface..."
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "ui/backend" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Starting Backend Server...${NC}"
cd ui/backend
../../.venv/bin/python app.py &
BACKEND_PID=$!
cd ../..

# Wait a moment for backend to start
sleep 3

# Check if backend is healthy
if wget -q --spider http://localhost:5000/api/health 2>/dev/null; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Backend might still be starting...${NC}"
fi

echo ""
echo "=========================================="
echo -e "${BLUE}🎉 HVAC-LLM UI is ready!${NC}"
echo "=========================================="
echo ""
echo "🔗 Open your browser and go to:"
echo -e "${GREEN}   http://localhost:5000${NC}"
echo ""
echo "📚 Features available:"
echo "  • Upload base IDF files"
echo "  • Natural language HVAC requests"
echo "  • Real-time AI agent monitoring"
echo "  • Download generated IDF files"
echo ""
echo "⚡ Backend API also available at:"
echo "   http://localhost:5000/api/health"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping server..."
    kill $BACKEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for user interrupt
wait $BACKEND_PID