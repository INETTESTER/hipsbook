#!/bin/bash

# ======================
# Config
# ======================
USERS=10
SPAWN_RATE=1
RUN_TIME=1m
HOST="https://hipsbook.gbydigitaltech.co.th"

# ======================
# Report
# ======================
mkdir -p report

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# ======================
# Run Locust
# ======================
py -m locust -f locustfile.py \
  --host="$HOST" \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$RUN_TIME" \
  --headless \
  --html "report/live_smoke_${TIMESTAMP}.html" \
  --csv "report/live_smoke_${TIMESTAMP}"