#!/bin/bash

# Setup script for ngrok authentication

NGROK_BIN=~/bin/ngrok

# Check if ngrok is installed
if [ ! -f "$NGROK_BIN" ]; then
    echo "Error: ngrok not found at $NGROK_BIN"
    exit 1
fi

# Prompt for authtoken
echo "Please enter your ngrok authtoken:"
echo "(Get it from: https://dashboard.ngrok.com/get-started/your-authtoken)"
read -r AUTHTOKEN

# Add authtoken to ngrok
$NGROK_BIN config add-authtoken "$AUTHTOKEN"

echo ""
echo "Authtoken configured successfully!"
echo ""
echo "Now update the authtoken in ngrok.yml file or run:"
echo "  ./start_ngrok.sh"
