#!/bin/bash

# Change to the required directory
cd /root/caner || exit 1  # Exit if the directory does not exist

# Check if .venv exists, if not create it with uv
if [ ! -d ".venv" ]; then
    echo ".venv not found. Creating virtual environment with uv..."
    if command -v uv &> /dev/null; then
        uv venv
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create virtual environment."
            exit 1
        fi
        
        # Source the newly created virtual environment
        echo "Activating newly created virtual environment..."
        source .venv/bin/activate
        
        # Now sync with the activated environment
        echo "Syncing dependencies..."
        uv sync
        if [ $? -ne 0 ]; then
            echo "Error: Failed to sync dependencies."
            exit 1
        fi
        
        echo "Virtual environment created and synced."
    else
        echo "Error: uv command not found. Please install uv first."
        exit 1
    fi
else
    # Source the existing virtual environment
    if [ -f ".venv/bin/activate" ]; then
        echo "Activating existing virtual environment..."
        source .venv/bin/activate
    else
        echo "Error: .venv/bin/activate not found. Virtual environment is corrupted."
        exit 1
    fi
fi

# Command to run Gunicorn
COMMAND="gunicorn app:app -w 1 -b 0.0.0.0:30823"

# Check if Gunicorn is already running
if pgrep -f "gunicorn app:app" > /dev/null; then
    echo "Gunicorn is already running."
else
    echo "Starting Gunicorn..."
    nohup $COMMAND > gunicorn.log 2>&1 &  # Run command in background and redirect output
    echo "Gunicorn started."
fi
