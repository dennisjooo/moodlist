#!/bin/bash
#
# Script to run the FastAPI application with uvicorn
#

set -e  # Exit on any error

# Default values
HOST="127.0.0.1"
PORT="8000"
WORKERS="1"
LOG_LEVEL="info"
ACCESS_LOG=""
RELOAD=""
RELOAD_DELAY="0.25"
APP="app.main:app"
LOOP="auto"
HTTP="auto"
WS="auto"
LOG_FILE=""

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Run the FastAPI application with uvicorn.

OPTIONS:
    --host HOST              Host to bind the server to (default: $HOST)
    --port PORT              Port to bind the server to (default: $PORT)
    --workers WORKERS        Number of worker processes (default: $WORKERS)
    --reload                 Enable auto-reload for development
    --reload-delay DELAY     Delay between reload checks (default: $RELOAD_DELAY)
    --log-level LEVEL        Set the logging level: critical, error, warning, info, debug, trace (default: $LOG_LEVEL)
    --access-log             Enable access logging
    --no-access-log          Disable access logging (default)
    --log-file FILE          Log output to file using tee (outputs to both console and file)
    --app APP                ASGI application to run (default: $APP)
    --loop LOOP              Event loop implementation: auto, asyncio, uvloop (default: $LOOP)
    --http HTTP              HTTP protocol implementation: auto, h11, httptools (default: $HTTP)
    --ws WS                  WebSocket protocol implementation: auto, websockets, wsproto (default: $WS)
    --help                   Show this help message

EXAMPLES:
    $0 --reload --log-level debug
    $0 --host 0.0.0.0 --port 8080 --workers 4
    $0 --reload --access-log --log-file server.log
    $0 --log-level info --log-file /var/log/moodlist/app.log

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        --reload)
            RELOAD="--reload"
            shift
            ;;
        --reload-delay)
            RELOAD_DELAY="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --access-log)
            ACCESS_LOG="--access-log"
            shift
            ;;
        --no-access-log)
            ACCESS_LOG=""
            shift
            ;;
        --log-file)
            LOG_FILE="$2"
            shift 2
            ;;
        --app)
            APP="$2"
            shift 2
            ;;
        --loop)
            LOOP="$2"
            shift 2
            ;;
        --http)
            HTTP="$2"
            shift 2
            ;;
        --ws)
            WS="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

# Validate log level
case $LOG_LEVEL in
    critical|error|warning|info|debug|trace) ;;
    *)
        echo "Invalid log level: $LOG_LEVEL" >&2
        echo "Valid options: critical, error, warning, info, debug, trace" >&2
        exit 1
        ;;
esac

# Validate loop
case $LOOP in
    auto|asyncio|uvloop) ;;
    *)
        echo "Invalid loop: $LOOP" >&2
        echo "Valid options: auto, asyncio, uvloop" >&2
        exit 1
        ;;
esac

# Validate http
case $HTTP in
    auto|h11|httptools) ;;
    *)
        echo "Invalid http: $HTTP" >&2
        echo "Valid options: auto, h11, httptools" >&2
        exit 1
        ;;
esac

# Validate ws
case $WS in
    auto|websockets|wsproto) ;;
    *)
        echo "Invalid ws: $WS" >&2
        echo "Valid options: auto, websockets, wsproto" >&2
        exit 1
        ;;
esac

# Build the uvicorn command
CMD="uvicorn $APP --host $HOST --port $PORT --workers $WORKERS --log-level $LOG_LEVEL --loop $LOOP --http $HTTP --ws $WS --timeout-keep-alive 75"

# Add optional flags
if [[ -n "$ACCESS_LOG" ]]; then
    CMD="$CMD $ACCESS_LOG"
fi

if [[ -n "$RELOAD" ]]; then
    CMD="$CMD $RELOAD --reload-delay $RELOAD_DELAY"
fi

# Display startup information
echo "Starting server with command: $CMD"
echo "Server will be available at: http://$HOST:$PORT"
echo "API documentation at: http://$HOST:$PORT/docs"
echo

# Change to the backend directory (in case script is run from elsewhere)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
cd "$BACKEND_DIR"

# Activate virtual environment if it exists and isn't already activated
if [[ -z "$VIRTUAL_ENV" && -d ".venv" ]]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Run uvicorn
if [[ -n "$LOG_FILE" ]]; then
    echo "Logging output to file: $LOG_FILE"
    exec $CMD | tee "$LOG_FILE"
else
    exec $CMD
fi
