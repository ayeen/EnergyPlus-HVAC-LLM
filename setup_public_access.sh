#!/bin/bash

# Complete setup and start script for public IP access

PUBLIC_IP="163.180.125.76"
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "========================================="
echo "  EnergyPlus HVAC-LLM"
echo "  Public IP Access Setup"
echo "========================================="
echo ""
echo "Public IP: $PUBLIC_IP"
echo ""

# Step 1: Open firewall (if needed)
echo "Step 1: Checking firewall..."
echo ""
echo "⚠️  Make sure ports 3000 and 5000 are open in your firewall!"
echo ""
echo "To open ports, run:"
echo "  sudo ufw allow 3000/tcp"
echo "  sudo ufw allow 5000/tcp"
echo ""
read -p "Press Enter when firewall is configured (or if no firewall)..."

# Step 2: Start Backend
echo ""
echo "Step 2: Starting Backend..."
cd "$PROJECT_ROOT/ui/backend"
python app.py > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✓ Backend started (PID: $BACKEND_PID)"
echo "  Log: tail -f backend.log"

# Wait for backend
sleep 5

# Step 3: Start Frontend
echo ""
echo "Step 3: Starting Frontend..."
cd "$PROJECT_ROOT/ui/frontend"
npm start > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "✓ Frontend started (PID: $FRONTEND_PID)"
echo "  Log: tail -f frontend.log"

# Wait for services to initialize
echo ""
echo "Waiting for services to initialize..."
sleep 10

# Step 4: Test connections
echo ""
echo "Step 4: Testing connections..."
echo ""

# Test backend
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✅ Backend is accessible"
else
    echo "⚠️  Backend might still be starting... check backend.log"
fi

# Test frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is accessible"
else
    echo "⚠️  Frontend might still be starting... check frontend.log"
fi

# Final instructions
echo ""
echo "========================================="
echo "  🎉 Setup Complete!"
echo "========================================="
echo ""
echo "Your application is now accessible at:"
echo ""
echo "🌐 Frontend: http://$PUBLIC_IP:3000"
echo "🔌 Backend:  http://$PUBLIC_IP:5000"
echo ""
echo "Share the Frontend URL with others!"
echo ""
echo "========================================="
echo "  Monitoring"
echo "========================================="
echo ""
echo "View logs:"
echo "  Backend:  tail -f $PROJECT_ROOT/backend.log"
echo "  Frontend: tail -f $PROJECT_ROOT/frontend.log"
echo ""
echo "Check status:"
echo "  $PROJECT_ROOT/check_public_access.sh"
echo ""
echo "Stop services:"
echo "  pkill -f 'python.*app.py'"
echo "  pkill -f 'react-scripts'"
echo ""
