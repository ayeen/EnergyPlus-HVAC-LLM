#!/bin/bash

# Script to start ngrok tunnels for frontend and backend

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NGROK_BIN=~/bin/ngrok
CONFIG_FILE="$SCRIPT_DIR/ngrok.yml"

# Check if ngrok is installed
if [ ! -f "$NGROK_BIN" ]; then
    echo "Error: ngrok not found at $NGROK_BIN"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file not found at $CONFIG_FILE"
    exit 1
fi

# Check if authtoken is set
if grep -q "YOUR_AUTH_TOKEN_HERE" "$CONFIG_FILE"; then
    echo "Error: Please set your ngrok authtoken in $CONFIG_FILE"
    echo "Get your token from: https://dashboard.ngrok.com/get-started/your-authtoken"
    exit 1
fi

echo "Starting ngrok tunnels..."
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start ngrok with config file
$NGROK_BIN start --all --config "$CONFIG_FILE"
