#!/bin/bash

# Quick Start Script - Start everything needed for public access

echo "========================================="
echo "  EnergyPlus HVAC-LLM - Public Access"
echo "========================================="
echo ""

# Check if ngrok is configured
if grep -q "YOUR_AUTH_TOKEN_HERE" ngrok.yml 2>/dev/null; then
    echo "⚠️  Ngrok not configured yet!"
    echo ""
    echo "Please run: ./setup_ngrok.sh"
    echo "Or get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

# Check if backend is running
if ! curl -s http://localhost:5000 > /dev/null 2>&1; then
    echo "⚠️  Backend not running!"
    echo ""
    echo "Start backend in a new terminal:"
    echo "  cd ui/backend && python app.py"
    echo ""
    read -p "Press Enter when backend is ready..."
fi

# Check if frontend is running
if ! curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "⚠️  Frontend not running!"
    echo ""
    echo "Start frontend in a new terminal:"
    echo "  cd ui/frontend && npm start"
    echo ""
    read -p "Press Enter when frontend is ready..."
fi

echo "✓ Backend is running"
echo "✓ Frontend is running"
echo ""
echo "Starting ngrok tunnels..."
echo ""

# Start ngrok
./start_ngrok.sh
