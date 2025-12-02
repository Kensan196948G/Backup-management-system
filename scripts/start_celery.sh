#!/bin/bash
# ==============================================================================
# Celery Worker Startup Script
# Phase 11: Asynchronous Task Processing
#
# This script starts Celery workers with proper configuration for
# the Backup Management System.
# ==============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/celery"
PID_DIR="$PROJECT_ROOT/pids"

# Default settings
WORKERS=${CELERY_WORKERS:-2}
CONCURRENCY=${CELERY_CONCURRENCY:-4}
LOG_LEVEL=${CELERY_LOG_LEVEL:-INFO}
QUEUES=${CELERY_QUEUES:-"default,email,notifications,reports,verification,maintenance"}

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"

# Activate virtual environment if exists
if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Change to project directory
cd "$PROJECT_ROOT"

# Export Flask environment
export FLASK_ENV=${FLASK_ENV:-development}

# Function to start worker
start_worker() {
    echo "Starting Celery worker..."
    celery -A celery_worker.celery_app worker \
        --loglevel="$LOG_LEVEL" \
        --concurrency="$CONCURRENCY" \
        --queues="$QUEUES" \
        --pidfile="$PID_DIR/celery-worker.pid" \
        --logfile="$LOG_DIR/celery-worker.log" \
        --detach
    echo "Worker started (PID: $(cat $PID_DIR/celery-worker.pid))"
}

# Function to start beat scheduler
start_beat() {
    echo "Starting Celery beat scheduler..."
    celery -A celery_worker.celery_app beat \
        --loglevel="$LOG_LEVEL" \
        --pidfile="$PID_DIR/celery-beat.pid" \
        --logfile="$LOG_DIR/celery-beat.log" \
        --detach
    echo "Beat started (PID: $(cat $PID_DIR/celery-beat.pid))"
}

# Function to start flower
start_flower() {
    echo "Starting Flower monitoring..."
    celery -A celery_worker.celery_app flower \
        --port="${FLOWER_PORT:-5555}" \
        --persistent=True \
        --db="$PROJECT_ROOT/data/flower.db" \
        --logging="$LOG_LEVEL" \
        &
    echo $! > "$PID_DIR/celery-flower.pid"
    echo "Flower started on port ${FLOWER_PORT:-5555}"
}

# Function to stop all services
stop_all() {
    echo "Stopping Celery services..."

    for pid_file in "$PID_DIR"/celery-*.pid; do
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "Stopping process $pid..."
                kill "$pid"
            fi
            rm -f "$pid_file"
        fi
    done

    echo "All Celery services stopped."
}

# Function to check status
status() {
    echo "Celery Service Status:"
    echo "======================"

    for service in worker beat flower; do
        pid_file="$PID_DIR/celery-$service.pid"
        if [ -f "$pid_file" ]; then
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "✅ $service: Running (PID: $pid)"
            else
                echo "❌ $service: Not running (stale PID file)"
            fi
        else
            echo "❌ $service: Not running"
        fi
    done
}

# Parse command
case "${1:-start}" in
    start)
        start_worker
        start_beat
        ;;
    start-worker)
        start_worker
        ;;
    start-beat)
        start_beat
        ;;
    start-flower)
        start_flower
        ;;
    start-all)
        start_worker
        start_beat
        start_flower
        ;;
    stop)
        stop_all
        ;;
    restart)
        stop_all
        sleep 2
        start_worker
        start_beat
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|start-worker|start-beat|start-flower|start-all|stop|restart|status}"
        echo ""
        echo "Commands:"
        echo "  start        - Start worker and beat"
        echo "  start-worker - Start only worker"
        echo "  start-beat   - Start only beat scheduler"
        echo "  start-flower - Start Flower monitoring UI"
        echo "  start-all    - Start worker, beat, and flower"
        echo "  stop         - Stop all Celery services"
        echo "  restart      - Restart worker and beat"
        echo "  status       - Show service status"
        echo ""
        echo "Environment variables:"
        echo "  CELERY_WORKERS     - Number of workers (default: 2)"
        echo "  CELERY_CONCURRENCY - Concurrency per worker (default: 4)"
        echo "  CELERY_LOG_LEVEL   - Log level (default: INFO)"
        echo "  CELERY_QUEUES      - Queues to consume (default: all)"
        echo "  FLOWER_PORT        - Flower UI port (default: 5555)"
        exit 1
        ;;
esac
