#!/bin/sh
# Start SQLBot on Railway: one process serves the web app, the API and the MCP
# server on $PORT. Any failure exits non-zero so Railway's restart policy applies.
set -eu

export PORT="${PORT:-8000}"

# Resources of this container (cgroup v2, then v1), not of the host.
mem_mb=""
if [ -r /sys/fs/cgroup/memory.max ]; then
  v=$(cat /sys/fs/cgroup/memory.max)
  [ "$v" != "max" ] && mem_mb=$((v / 1048576))
elif [ -r /sys/fs/cgroup/memory/memory.limit_in_bytes ]; then
  v=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
  [ "$v" -lt 1125899906842624 ] && mem_mb=$((v / 1048576))
fi
cpus=1
if [ -r /sys/fs/cgroup/cpu.max ]; then
  read -r quota period < /sys/fs/cgroup/cpu.max || true
  if [ "${quota:-max}" != "max" ] && [ "${period:-0}" -gt 0 ]; then
    cpus=$(( (quota + period - 1) / period ))
  else
    cpus=$(nproc)
  fi
fi
[ "$cpus" -gt 4 ] && cpus=4
[ "$cpus" -lt 1 ] && cpus=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-$cpus}" MKL_NUM_THREADS="${MKL_NUM_THREADS:-$cpus}"
export SQLBOT_MEMORY_LIMIT_MB="${mem_mb:-0}"

# The local embedding model (RAG over tables, terminology and training data)
# needs about 1 GB on its own. Below 1.5 GB it would get the service
# OOM-killed, so it stays off unless you set EMBEDDING_ENABLED yourself.
min_mb="${SQLBOT_EMBEDDING_MIN_MB:-1536}"
if [ -n "$mem_mb" ] && [ "$mem_mb" -lt "$min_mb" ]; then
  export EMBEDDING_ENABLED="${EMBEDDING_ENABLED:-false}"
  export TABLE_EMBEDDING_ENABLED="${TABLE_EMBEDDING_ENABLED:-false}"
  echo "railway: ${mem_mb} MB RAM limit, local embeddings off (need about ${min_mb} MB)"
fi

# Everything SQLBot writes lives on the volume at /opt/sqlbot/data.
export EXCEL_PATH="${EXCEL_PATH:-/opt/sqlbot/data/excel}"
export UPLOAD_DIR="${UPLOAD_DIR:-/opt/sqlbot/data/file}"
export MCP_IMAGE_PATH="${MCP_IMAGE_PATH:-/opt/sqlbot/data/images}"
mkdir -p "$EXCEL_PATH" "$UPLOAD_DIR" "$MCP_IMAGE_PATH"

# Chart pictures for MCP answers are rendered by the bundled g2-ssr helper and
# served at https://<your domain>/images/.
export MCP_IMAGE_HOST="${MCP_IMAGE_HOST:-http://127.0.0.1:3000}"
if [ -n "${RAILWAY_PUBLIC_DOMAIN:-}" ]; then
  export SERVER_IMAGE_HOST="${SERVER_IMAGE_HOST:-https://${RAILWAY_PUBLIC_DOMAIN}/images/}"
fi
export PG_POOL_SIZE="${PG_POOL_SIZE:-10}" PG_MAX_OVERFLOW="${PG_MAX_OVERFLOW:-10}"
export MALLOC_ARENA_MAX="${MALLOC_ARENA_MAX:-2}"

cd /opt/sqlbot/app

# Wait for PostgreSQL, migrate (under a lock), lock the admin account with the
# generated password and register the deployer's LLM.
python /opt/sqlbot/railway/railway_init.py

# Chart renderer for MCP answers; restarted if it ever stops.
(
  cd /opt/sqlbot/g2-ssr
  while true; do
    node --max-old-space-size=96 app.js > /dev/null 2>&1 || true
    sleep 3
  done
) &

exec uvicorn railway_entry:application --app-dir /opt/sqlbot/railway \
  --host 0.0.0.0 --port "$PORT" --workers 1 \
  --proxy-headers --forwarded-allow-ips '*' --timeout-keep-alive 65
