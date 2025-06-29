#!/bin/bash
export PATH="/root/.local/bin:$PATH"

# Change to the required directory
cd /root/caner || exit 1  # Exit if the directory does not exist

#Command to run Gunicorn
COMMAND="uv run --project /root/caner gunicorn app:app -w 1 -b 0.0.0.0:30823"
PGREP_PATTERN="gunicorn app:app.*30823"

# Check if Gunicorn is already running
if pgrep -f "$PGREP_PATTERN" > /dev/null; then
    echo "Gunicorn is already running."
else
    echo "Starting Gunicorn..."
    nohup $COMMAND > gunicorn.log 2>&1 &  # Run command in background and redirect output
    echo "Gunicorn started."
fi
