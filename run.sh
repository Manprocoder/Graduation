#!/bin/bash
#-- local web gui
#-----------------------------------
#-- check processes using port 5000 and kill all 
#-- to avoid app crash
##-------------------------------------
export GST_DEBUG=3   #debug

# Check if required commands are available
command -v lsof >/dev/null 2>&1 || { echo >&2 "lsof command not found. Please install it first."; exit 1; }
command -v gunicorn >/dev/null 2>&1 || { echo >&2 "gunicorn command not found. Please install it first."; exit 1; }

# Check for any processes using port 5000
echo "Checking for processes using port 5000..."
PORT=5000
PROCESSES=$(lsof -t -i:$PORT)

if [ -z "$PROCESSES" ]; then
    echo "No processes are using port $PORT."
else
    echo "Found processes using port $PORT: $PROCESSES"
    
    # Kill those processes
    for PID in $PROCESSES; do
        echo "Killing process $PID..."
        # Try to kill gracefully first
        kill $PID || {
            # If not successful, use kill -9
            echo "Process $PID could not be killed gracefully. Trying with kill -9..."
            [ "$(id -u)" = "0" ] && kill -9 $PID || sudo kill -9 $PID
        }
    done
fi

# Start the Gunicorn server
echo "Starting Gunicorn server..."
gunicorn -w 4 -k gthread -t 120 --threads 4 --bind 0.0.0.0:5000 gui:app

# Print completion message
echo "Gunicorn server started successfully."