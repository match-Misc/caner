#!/bin/bash

# 1. Navigate to the project directory
# Replace with your actual path
cd /root/caner || exit

# 2. Fetch the latest metadata from the remote
git fetch origin

# 3. Get the Commit Hashes
UPSTREAM=${1:-'@{u}'}
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse "$UPSTREAM")
BASE=$(git merge-base @ "$UPSTREAM") # <--- This was missing before

# 4. Compare and Act
if [ "$LOCAL" = "$REMOTE" ]; then
    echo "No changes detected. Current version: $LOCAL"
elif [ "$LOCAL" = "$BASE" ]; then
    echo "New updates detected on remote. Pulling..."
    
    # Pull changes
    git pull origin main

    # Restart Gunicorn
    echo "Reloading Gunicorn..."
    pkill -HUP gunicorn
    
    echo "Deployment complete."
elif [ "$REMOTE" = "$BASE" ]; then
    echo "Local changes detected (ahead of remote). No action taken."
else
    echo "Diverged branches (manual intervention required)."
fi
