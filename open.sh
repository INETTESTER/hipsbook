#!/bin/bash

# ======================
# Test Config
# ======================
USERS=10
SPAWN_RATE=1
RUN_TIME="10s"

HOST="https://hipsbook.gbydigitaltech.co.th"

# realistic | stress
PROFILE="realistic"

# ======================
# Report Folder
# ======================
DATE=$(date +"%d-%m-%Y")
TIME=$(date +"%H-%M-%S")

REPORT_DIR="report/${USERS}users_${DATE}_${TIME}"

mkdir -p "$REPORT_DIR"

# ======================
# Display Config
# ======================
echo "==================================="
echo " Users       : $USERS"
echo " Spawn Rate  : $SPAWN_RATE"
echo " Run Time    : $RUN_TIME"
echo " Profile     : $PROFILE"
echo " Report Dir  : $REPORT_DIR"
echo "==================================="

# ======================
# Run Locust
# ======================
TEST_PROFILE=$PROFILE py -m locust \
  -f locustfile.py \
  --host="$HOST" \
  --users "$USERS" \
  --spawn-rate "$SPAWN_RATE" \
  --run-time "$RUN_TIME" \
  --headless \
  --html "$REPORT_DIR/report.html" \
  --csv "$REPORT_DIR/result"

# ======================
# Finish
# ======================
echo ""
echo "==================================="
echo " Test Finished"
echo " Report saved to:"
echo " $REPORT_DIR"
echo "==================================="