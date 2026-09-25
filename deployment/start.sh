#!/bin/sh
set -eu

mkdir -p /data
ollama serve >/tmp/ollama.log 2>&1 &

attempt=0
until curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; do
  attempt=$((attempt + 1))
  if [ "$attempt" -ge 60 ]; then
    cat /tmp/ollama.log
    exit 1
  fi
  sleep 1
done

exec python -m uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers
