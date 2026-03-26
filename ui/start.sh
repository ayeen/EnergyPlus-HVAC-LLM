#!/bin/bash

# Startup script for HVAC-LLM UI
# This script starts both backend and frontend servers

echo "=================================="
echo "HVAC-LLM UI Startup Script"
echo "=================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -d "ui/backend" ] || [ ! -d "ui/frontend" ]; then
    echo -e "${RED}Error: Please run this script from the project root directory${NC}"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend
echo -e "${GREEN}Starting Backend Server...${NC}"
cd ui/backend
../../.venv/bin/python app.py > ../../backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
    echo "  URL: http://localhost:5000"
    echo "  Logs: backend.log"
else
    echo -e "${RED}✗ Failed to start backend${NC}"
    exit 1
fi

echo ""

# Skip health check - start frontend immediately
echo -e "${YELLOW}Note: Backend is starting (Mistral model loading may take 1-2 minutes)${NC}"
echo ""

# Start Frontend
echo -e "${GREEN}Starting Frontend Server...${NC}"
cd ui/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies (first time setup)...${NC}"
    npm install
fi

npm start > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
    echo "  URL: http://localhost:3000"
    echo "  Logs: frontend.log"
else
    echo -e "${RED}✗ Failed to start frontend${NC}"
    kill $BACKEND_PID
    exit 1
fi

echo ""
echo "=================================="
echo -e "${GREEN}Both servers are running!${NC}"
echo "=================================="
echo ""
echo "Backend:  http://localhost:5000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt
wait
