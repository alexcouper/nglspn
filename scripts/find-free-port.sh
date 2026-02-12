#!/bin/bash
# Find a free port starting from a given base port
# Usage: find-free-port.sh [base_port]
# Returns the first available port

BASE_PORT=${1:-8000}

for port in $(seq $BASE_PORT $((BASE_PORT + 100))); do
    if ! lsof -i :$port >/dev/null 2>&1; then
        echo $port
        exit 0
    fi
done

echo "No free port found in range $BASE_PORT-$((BASE_PORT + 100))" >&2
exit 1
