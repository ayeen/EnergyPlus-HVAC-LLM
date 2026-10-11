#!/bin/bash

# Script to check and display public access information

echo "========================================="
echo "  Public IP Access Configuration"
echo "========================================="
echo ""

# Get public IP
PUBLIC_IP="163.180.125.76"
echo "📍 Your Public IP: $PUBLIC_IP"
echo ""

# Check if services are running
echo "🔍 Checking Services..."
echo ""

# Check backend
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    echo "✅ Backend is running (Port 5000)"
    echo "   Local:  http://localhost:5000"
    echo "   Public: http://$PUBLIC_IP:5000"
else
    echo "❌ Backend is NOT running"
    echo "   Start with: cd ui/backend && python app.py"
fi

echo ""

# Check frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is running (Port 3000)"
    echo "   Local:  http://localhost:3000"
    echo "   Public: http://$PUBLIC_IP:3000"
else
    echo "❌ Frontend is NOT running"
    echo "   Start with: cd ui/frontend && npm start"
fi

echo ""
echo "========================================="
echo "  Firewall Status"
echo "========================================="
echo ""

# Check firewall status for required ports
if command -v ufw &> /dev/null; then
    echo "🔥 UFW Firewall Status:"
    sudo ufw status | grep -E "3000|5000|Status"
elif command -v firewall-cmd &> /dev/null; then
    echo "🔥 Firewalld Status:"
    sudo firewall-cmd --list-ports
else
    echo "⚠️  No standard firewall detected"
fi

echo ""
echo "========================================="
echo "  Access URLs"
echo "========================================="
echo ""
echo "Share these URLs with others:"
echo ""
echo "🌐 Frontend: http://$PUBLIC_IP:3000"
echo "🔌 Backend:  http://$PUBLIC_IP:5000"
echo ""
echo "Users only need the Frontend URL to access your application!"
echo ""
