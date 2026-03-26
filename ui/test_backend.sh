#!/bin/bash

# Simple test script to verify backend setup
cd /home/hubel/Documents/Ayeen/EnergyPlus-HVAC-LLM/ui/backend

echo "Testing backend import..."
../../.venv/bin/python -c "from routes.upload import upload_bp; print('✓ Imports successful')"

if [ $? -eq 0 ]; then
    echo "✓ Backend modules can be imported correctly"
    echo ""
    echo "You can now run: ./ui/start.sh"
else
    echo "✗ Import error - check the output above"
fi
