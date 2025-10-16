#!/bin/bash
# Run the price updater in the background with logging
# This script ensures the process continues even if SSH disconnects
# Works on: AWS EC2, GCP, Azure, any Linux VM

# Activate virtual environment
source ~/price_updaters/venv/bin/activate

# Navigate to project directory
cd ~/price_updaters

# Start Xvfb (virtual display) in the background
echo "Starting virtual display..."
Xvfb :99 -screen 0 1920x1080x24 > /dev/null 2>&1 &
export DISPLAY=:99

# Wait a moment for Xvfb to start
sleep 2

# Create logs directory
mkdir -p logs

# Get timestamp for log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOGFILE="logs/orchestrator_${TIMESTAMP}.log"

echo "================================"
echo "Starting Price Updater"
echo "================================"
echo "Log file: $LOGFILE"
echo "Process will run in background"
echo ""

# Run the orchestrator in background with nohup
# This ensures it continues even if SSH disconnects
nohup python orchestrator.py test_with_matched.csv > "$LOGFILE" 2>&1 &

# Get the process ID
PID=$!
echo "Process ID: $PID"
echo "$PID" > price_updater.pid

echo ""
echo "✅ Price updater started successfully!"
echo ""
echo "To monitor progress:"
echo "  tail -f $LOGFILE"
echo ""
echo "To check if running:"
echo "  ps aux | grep python"
echo ""
echo "To stop the process:"
echo "  kill $PID"
echo "  or"
echo "  kill \$(cat price_updater.pid)"
echo ""
echo "To view logs later:"
echo "  ls -lh logs/"
echo "  cat $LOGFILE"
echo "================================"
