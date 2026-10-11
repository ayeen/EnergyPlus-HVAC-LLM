#!/bin/bash

# Script to open firewall ports for public access

PUBLIC_IP="163.180.125.76"

echo "========================================="
echo "  Opening Firewall Ports"
echo "========================================="
echo ""

# Check which firewall is in use
if command -v ufw &> /dev/null; then
    echo "Using UFW firewall..."
    echo ""
    echo "Opening ports 3000 and 5000..."
    sudo ufw allow 3000/tcp comment 'React Frontend'
    sudo ufw allow 5000/tcp comment 'Flask Backend'
    echo ""
    echo "Firewall rules updated!"
    echo ""
    sudo ufw status numbered

elif command -v firewall-cmd &> /dev/null; then
    echo "Using firewalld..."
    echo ""
    echo "Opening ports 3000 and 5000..."
    sudo firewall-cmd --permanent --add-port=3000/tcp
    sudo firewall-cmd --permanent --add-port=5000/tcp
    sudo firewall-cmd --reload
    echo ""
    echo "Firewall rules updated!"
    echo ""
    sudo firewall-cmd --list-ports

else
    echo "⚠️  No standard firewall detected (ufw or firewalld)"
    echo ""
    echo "You may need to manually configure your firewall:"
    echo "  - Allow incoming TCP on port 3000 (Frontend)"
    echo "  - Allow incoming TCP on port 5000 (Backend)"
fi

echo ""
echo "========================================="
echo "  Testing Access"
echo "========================================="
echo ""
echo "Testing from localhost..."
echo ""

# Test backend
if curl -s http://localhost:5000/api/health > /dev/null; then
    echo "✅ Backend accessible locally"
else
    echo "❌ Backend not accessible - make sure it's running"
fi

# Test frontend
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ Frontend accessible locally"
else
    echo "❌ Frontend not accessible - make sure it's running"
fi

echo ""
echo "========================================="
echo "  Public URLs"
echo "========================================="
echo ""
echo "Your application is now accessible at:"
echo ""
echo "🌐 Frontend: http://$PUBLIC_IP:3000"
echo "🔌 Backend:  http://$PUBLIC_IP:5000"
echo ""
