#!/bin/bash

# Get ngrok public URLs

echo "Fetching ngrok public URLs..."
echo ""

# Query ngrok API
RESPONSE=$(curl -s http://localhost:4040/api/tunnels)

if [ $? -ne 0 ] || [ -z "$RESPONSE" ]; then
    echo "Error: Cannot connect to ngrok API. Make sure ngrok is running."
    echo "Start ngrok with: ./start_ngrok.sh"
    exit 1
fi

# Parse and display URLs
echo "==================================="
echo "Your Public URLs:"
echo "==================================="
echo ""

# Extract frontend URL
FRONTEND_URL=$(echo "$RESPONSE" | grep -o '"public_url":"https://[^"]*"' | grep '3000' | head -1 | cut -d'"' -f4)
if [ -n "$FRONTEND_URL" ]; then
    echo "Frontend (React): $FRONTEND_URL"
else
    echo "Frontend: Not found"
fi

# Extract backend URL
BACKEND_URL=$(echo "$RESPONSE" | grep -o '"public_url":"https://[^"]*"' | grep '5000' | head -1 | cut -d'"' -f4)
if [ -n "$BACKEND_URL" ]; then
    echo "Backend (Flask):  $BACKEND_URL"
else
    echo "Backend: Not found"
fi

echo ""
echo "==================================="
echo ""
echo "Share these URLs with others to access your application!"
echo "View ngrok dashboard at: http://localhost:4040"
