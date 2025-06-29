#!/bin/bash

# Script configuration
SCRIPT_NAME="run_data_fetcher.sh"
WORK_DIR="/root/caner"  # Update this path
LOG_FILE="data_fetcher.log"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Start logging
log_message "=== $SCRIPT_NAME started ==="

# Change to working directory
if ! cd "$WORK_DIR"; then
    log_message "ERROR: Failed to change directory to $WORK_DIR"
    exit 1
fi

log_message "Changed to directory: $(pwd)"

# Set PATH to include common locations where uv might be installed
export PATH="/usr/local/bin:/usr/bin:/bin:/root/.local/bin:/root/.cargo/bin:$PATH"

# Check if uv command exists
if ! command -v uv >/dev/null 2>&1; then
    log_message "ERROR: uv command not found in PATH: $PATH"
    exit 1
fi

log_message "Found uv at: $(which uv)"

# Check if .venv exists, if not create it with uv
if [ ! -d ".venv" ]; then
    log_message ".venv not found. Creating virtual environment with uv..."
    if uv venv >> "$LOG_FILE" 2>&1; then
        log_message "Virtual environment created successfully"
        
        # Source the newly created virtual environment
        log_message "Activating newly created virtual environment..."
        source .venv/bin/activate
        
        # Now sync dependencies
        log_message "Syncing dependencies..."
        if uv sync >> "$LOG_FILE" 2>&1; then
            log_message "Dependencies synced successfully"
        else
            log_message "ERROR: Failed to sync dependencies"
            exit 1
        fi
    else
        log_message "ERROR: Failed to create virtual environment"
        exit 1
    fi
else
    # Source the existing virtual environment
    if [ -f ".venv/bin/activate" ]; then
        log_message "Activating existing virtual environment..."
        source .venv/bin/activate
        
        # Update dependencies for existing environment
        log_message "Syncing dependencies..."
        if uv sync >> "$LOG_FILE" 2>&1; then
            log_message "Dependencies synced successfully"
        else
            log_message "WARNING: Failed to sync dependencies, continuing anyway..."
        fi
    else
        log_message "ERROR: .venv/bin/activate not found. Virtual environment is corrupted."
        exit 1
    fi
fi

# Run the data fetcher and capture both stdout and stderr
log_message "Starting data_fetcher.py..."

if uv run data_fetcher.py >> "$LOG_FILE" 2>&1; then
    log_message "data_fetcher.py completed successfully"
else
    log_message "ERROR: data_fetcher.py failed with exit code $?"
fi

log_message "=== $SCRIPT_NAME finished ==="
