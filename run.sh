#!/bin/bash
# IBKR Trading Bot Runner
# Usage: ./run.sh [start|stop|status|logs]

BOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$BOT_DIR/bot.pid"
LOG_FILE="$BOT_DIR/logs/bot.log"
VENV_DIR="$BOT_DIR/.venv"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Bot is already running (PID: $(cat $PID_FILE))"
        exit 1
    fi

    echo "Starting IBKR Trading Bot..."
    cd "$BOT_DIR"
    source "$VENV_DIR/bin/activate"
    nohup python3 -m src -l INFO >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Bot started (PID: $(cat $PID_FILE))"
    echo "Logs: tail -f $LOG_FILE"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Bot is not running (no PID file)"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping bot (PID: $PID)..."
        kill -TERM "$PID"
        sleep 2
        if kill -0 "$PID" 2>/dev/null; then
            echo "Force killing..."
            kill -9 "$PID"
        fi
        rm -f "$PID_FILE"
        echo "Bot stopped"
    else
        echo "Bot is not running"
        rm -f "$PID_FILE"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "Bot is running (PID: $(cat $PID_FILE))"
        ps -p $(cat "$PID_FILE") -o pid,ppid,user,%cpu,%mem,etime,command
    else
        echo "Bot is not running"
        [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    fi
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "No log file found at $LOG_FILE"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    *)
        echo "Usage: $0 {start|stop|status|logs|restart}"
        exit 1
        ;;
esac
