#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DUMP_FILE="${SCRIPT_DIR}/prod-dump.sql"

# Load .env if present
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

# Validate required env vars
if [ -z "${PROD_DB_URL:-}" ]; then
    echo "Error: PROD_DB_URL is not set. Copy .env.example to .env and fill it in."
    exit 1
fi

if [ -z "${LOCAL_DB_URL:-}" ]; then
    echo "Error: LOCAL_DB_URL is not set. Copy .env.example to .env and fill it in."
    exit 1
fi

# Parse local DB URL to extract dbname for dropdb/createdb
# Format: postgres://user:pass@host:port/dbname
LOCAL_DB_NAME=$(echo "$LOCAL_DB_URL" | sed -E 's|.*://[^/]+/([^?]+).*|\1|')
LOCAL_DB_BASE=$(echo "$LOCAL_DB_URL" | sed -E 's|(.*://[^/]+/).*|\1|')

usage() {
    echo "Usage: $0 [dump|load|sync]"
    echo ""
    echo "  dump  - Dump production database to ${DUMP_FILE}"
    echo "  load  - Load dump file into local database"
    echo "  sync  - Dump production then load locally (dump + load)"
    echo ""
    echo "Requires PROD_DB_URL and LOCAL_DB_URL env vars (or .env file)."
}

dump_prod() {
    echo "==> Dumping production database..."
    pg_dump "$PROD_DB_URL" \
        --no-owner \
        --no-privileges \
        --format=custom \
        --file="$DUMP_FILE"
    echo "==> Dump saved to ${DUMP_FILE}"
}

load_local() {
    if [ ! -f "$DUMP_FILE" ]; then
        echo "Error: No dump file found at ${DUMP_FILE}. Run 'dump' first."
        exit 1
    fi

    # Build a maintenance URL pointing at the default 'postgres' database
    LOCAL_MAINTENANCE_URL=$(echo "$LOCAL_DB_URL" | sed -E 's|/([^/?]+)(\?.*)?$|/postgres\2|')

    echo "==> Dropping and recreating local database '${LOCAL_DB_NAME}'..."
    psql "$LOCAL_MAINTENANCE_URL" -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${LOCAL_DB_NAME}' AND pid <> pg_backend_pid();" >/dev/null 2>&1 || true
    psql "$LOCAL_MAINTENANCE_URL" -c "DROP DATABASE IF EXISTS \"${LOCAL_DB_NAME}\";"
    psql "$LOCAL_MAINTENANCE_URL" -c "CREATE DATABASE \"${LOCAL_DB_NAME}\";"

    echo "==> Restoring dump into local database..."
    pg_restore "$DUMP_FILE" \
        --dbname="$LOCAL_DB_URL" \
        --no-owner \
        --no-privileges \
        2>&1 | grep -v "WARNING:" || true

    echo "==> Local database '${LOCAL_DB_NAME}' restored."
}

case "${1:-sync}" in
    dump)
        dump_prod
        ;;
    load)
        load_local
        ;;
    sync)
        dump_prod
        load_local
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        echo "Unknown command: $1"
        usage
        exit 1
        ;;
esac
