#!/bin/bash

# 1. Navigate to the project directory
cd /root/caner || exit

# 2. Fetch the latest metadata from the remote (does not merge yet)
git fetch origin

# 3. Compare local HEAD with the remote HEAD
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ $LOCAL = $REMOTE ]; then
    echo "No changes detected. Current version: $LOCAL"
elif [ $LOCAL = $BASE ]; then
    echo "Need to pull"
    
    # 4. Pull changes
    git pull origin main

    # 5. Restart Gunicorn (Graceful Reload)
    # This sends a HUP signal to the master process to reload workers
    # without dropping connections.
    echo "Reloading Gunicorn..."
    pkill -HUP gunicorn
    
    # Alternatively, if you use a specific PID file:
    # kill -HUP $(cat /path/to/gunicorn.pid)
    
    echo "Deployment complete."
else
    echo "Diverged branches (manual intervention required)"
fi
