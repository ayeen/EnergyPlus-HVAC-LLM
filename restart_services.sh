#!/bin/bash

# Restart both frontend and backend services

echo "========================================="
echo "  Restarting Services"
echo "========================================="
echo ""

# Kill existing processes
echo "Stopping existing services..."
pkill -f "python.*app.py" 2>/dev/null
pkill -f "react-scripts" 2>/dev/null
sleep 2

# Go to project root
cd "$(dirname "$0")"

# Start backend
echo "Starting backend..."
cd ui/backend
python app.py > ../../backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend started (PID: $BACKEND_PID)"
cd ../..

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
cd ui/frontend
npm start > ../../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend started (PID: $FRONTEND_PID)"
cd ../..

echo ""
echo "========================================="
echo "  Services Started"
echo "========================================="
echo ""
echo "Backend PID:  $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "Logs:"
echo "  Backend:  tail -f backend.log"
echo "  Frontend: tail -f frontend.log"
echo ""
echo "Wait a few moments for services to initialize..."
sleep 5

echo ""
echo "Checking status..."
./check_public_access.sh
