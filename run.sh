#!/usr/bin/env bash
# Field Notes CMS — persistent local server manager.
#
# The dev server (python3 app.py) dies the moment its terminal closes — that is
# why the site "stopped working". This script runs the app under gunicorn as a
# detached background process that SURVIVES closing the terminal, and lets you
# start / stop / check / restart it with one command.
#
#   ./run.sh start     # start (or no-op if already up)
#   ./run.sh stop      # stop
#   ./run.sh restart   # stop + start (use after editing code)
#   ./run.sh status    # is it up? + health check
#   ./run.sh logs      # tail the server log
#
# Port: defaults to 8000, override with  PORT=9000 ./run.sh start
set -euo pipefail

cd "$(dirname "$0")"
PORT="${PORT:-8000}"
PIDFILE="run/server.pid"
LOGDIR="logs"
LOGFILE="$LOGDIR/server.log"
mkdir -p run "$LOGDIR"

# find gunicorn: PATH, then the pip --user bin dir
find_gunicorn() {
  if command -v gunicorn >/dev/null 2>&1; then echo "gunicorn"; return; fi
  local userbin
  userbin="$(python3 -c 'import site,os;print(os.path.join(site.getuserbase(),"bin","gunicorn"))' 2>/dev/null || true)"
  if [ -n "$userbin" ] && [ -x "$userbin" ]; then echo "$userbin"; return; fi
  echo ""   # not found
}

is_running() {
  [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null
}

start() {
  if is_running; then
    echo "already running (pid $(cat "$PIDFILE")) on port $PORT"
    return 0
  fi
  # ensure deps + database exist before we daemonize, so failures are visible
  python3 -c "import flask, PIL" 2>/dev/null || {
    echo "missing dependencies — run:  python3 -m pip install --user -r requirements.txt"; exit 1; }
  python3 -c "import db; db.init_db()" || { echo "database init failed"; exit 1; }

  local GUNICORN; GUNICORN="$(find_gunicorn)"
  if [ -z "$GUNICORN" ]; then
    echo "gunicorn not found — falling back to the dev server (less robust)."
    nohup python3 app.py >> "$LOGFILE" 2>&1 &
  else
    nohup "$GUNICORN" app:app --workers 2 --bind "0.0.0.0:$PORT" \
      --timeout 120 --access-logfile "$LOGFILE" --error-logfile "$LOGFILE" \
      >> "$LOGFILE" 2>&1 &
  fi
  echo $! > "$PIDFILE"
  sleep 2
  if is_running && curl -fs -o /dev/null "http://localhost:$PORT/healthz"; then
    echo "✅ started — http://localhost:$PORT   (admin: http://localhost:$PORT/admin)"
  else
    echo "❌ failed to start. Last log lines:"; tail -n 20 "$LOGFILE"; exit 1
  fi
}

stop() {
  if is_running; then
    kill "$(cat "$PIDFILE")" 2>/dev/null || true
    sleep 1
    pkill -f "gunicorn app:app" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "stopped"
  else
    pkill -f "gunicorn app:app" 2>/dev/null || true
    rm -f "$PIDFILE"
    echo "was not running"
  fi
}

status() {
  if is_running; then
    if curl -fs -o /dev/null "http://localhost:$PORT/healthz"; then
      echo "✅ up (pid $(cat "$PIDFILE")) and healthy on http://localhost:$PORT"
    else
      echo "⚠️  process alive (pid $(cat "$PIDFILE")) but not answering on $PORT — try: ./run.sh restart"
    fi
  else
    echo "⛔ not running — start with: ./run.sh start"
  fi
}

case "${1:-status}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    tail -n 60 -f "$LOGFILE" ;;
  *) echo "usage: ./run.sh {start|stop|restart|status|logs}"; exit 1 ;;
esac
