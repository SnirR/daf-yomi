#!/bin/bash

# Daf Yomi Web App Launcher
echo "⚡ Daf Yomi Web App - Lightning Fast ⚡"
echo "======================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Prefer project venv (Homebrew Python is PEP 668 externally-managed)
PYTHON="$SCRIPT_DIR/.venv/bin/python3"
if [ ! -x "$PYTHON" ]; then
    if command -v python3 &> /dev/null; then
        PYTHON="$(command -v python3)"
    else
        echo "❌ Python3 is not installed or not in PATH"
        exit 1
    fi
fi

# Check if required modules are available
"$PYTHON" -c "import flask, requests, bs4, curl_cffi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Required Python modules not found. Please install:"
    echo "   cd $SCRIPT_DIR && python3 -m venv .venv && .venv/bin/pip install flask requests beautifulsoup4 'curl-cffi>=0.13.0'"
    exit 1
fi

echo "🔥 Starting server..."

# Check if port 5001 is already in use
if lsof -Pi :5001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 5001 is already in use. Attempting to stop existing server..."
    # Try to kill existing Flask processes
    pkill -f "python.*app.py" 2>/dev/null || true
    sleep 1
fi

echo "✅ Starting."

# Start the Flask server in the background
"$PYTHON" app.py &
SERVER_PID=$!

# Wait a moment for the server to start
sleep 3

echo "✅ Started! Opening browser..."

# Open the browser
if command -v open &> /dev/null; then
    # macOS
    open http://localhost:5001
elif command -v xdg-open &> /dev/null; then
    # Linux
    xdg-open http://localhost:5001
elif command -v start &> /dev/null; then
    # Windows
    start http://localhost:5001
else
    echo "🌐 Server running at: http://localhost:5001"
fi

echo ""
echo "📖 Daf Yomi Web App is ready!"
echo "🌐 Close this window to stop server"
echo "❌ Ctrl+C to stop"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "❌ Stopped"
    kill $SERVER_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Wait for the server process
wait $SERVER_PID