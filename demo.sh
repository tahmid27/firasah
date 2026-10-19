#!/usr/bin/env bash
# Starts the dashboard on the synthetic demo data: the API on :8000 and the
# website on :3000. Ctrl+C stops both.   Usage: ./demo.sh
set -euo pipefail
cd "$(dirname "$0")"

API_PORT=8000
WEB_PORT=3000

# NO_BROWSER=1 ./demo.sh skips opening the browser.

# A stale key path in the shell would make BigQuery sign in as the wrong
# identity (see CLAUDE.md); the API uses your gcloud login instead
unset GOOGLE_APPLICATION_CREDENTIALS

for tool in uv npm curl; do
  command -v "$tool" >/dev/null || { echo "Missing '$tool'. Install it first."; exit 1; }
done

for port in "$API_PORT" "$WEB_PORT"; do
  if lsof -ti "tcp:$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port is already in use. Is the demo already running? Stop it first."
    exit 1
  fi
done

if command -v gcloud >/dev/null && ! gcloud auth application-default print-access-token >/dev/null 2>&1; then
  echo "Your Google sign-in for BigQuery has expired. Run this, then try again:"
  echo "  gcloud auth application-default login"
  exit 1
fi

if [ ! -d web/node_modules ]; then
  echo "Installing the website's packages (first run only)..."
  (cd web && npm install)
fi

# Ctrl+C (or either server exiting) stops everything this script started
trap 'trap - INT TERM EXIT; kill 0 2>/dev/null' INT TERM EXIT

label() { awk -v tag="$1" '{ print tag " " $0; fflush() }'; }

BIGQUERY_DATASET=firasah_synthetic uv run uvicorn main:app --port "$API_PORT" 2>&1 | label "[api]" &
(cd web && npm run dev -- --port "$WEB_PORT") 2>&1 | label "[web]" &

echo "Starting... (the first page load compiles the site and takes a few seconds)"
for _ in $(seq 1 60); do
  if curl -fs "http://localhost:$API_PORT/health" >/dev/null &&
    curl -fs -o /dev/null "http://localhost:$WEB_PORT/login"; then
    cat <<EOF

  Firasah demo is running:  http://localhost:$WEB_PORT

  Sign in as one of the demo charities (email / password):
    Al-Noor Community Trust   demo-small@example.com   demo-small
    Brightwater Foundation    demo-medium@example.com  demo-medium
    Unity Relief              demo-large@example.com   demo-large

  Press Ctrl+C to stop.

EOF
    if [ -z "${NO_BROWSER:-}" ] && command -v open >/dev/null; then
      open "http://localhost:$WEB_PORT/login"
    fi
    wait
    exit 0
  fi
  sleep 1
done

echo "The servers didn't start within a minute. Check the [api] and [web] lines above."
exit 1
