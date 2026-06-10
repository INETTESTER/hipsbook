#!/bin/bash

# ======================
# Mode
# ======================
# local | master | worker
MODE="local"

# ใช้เฉพาะ worker
MASTER_HOST="10.0.0.1"

# ใช้เฉพาะ master
EXPECT_WORKERS=2

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
# Report Config
# ======================
DATE=$(date +"%d-%m-%Y")
TIME=$(date +"%H-%M-%S")

REPORT_DIR="report/${USERS}users_${DATE}_${TIME}"

# ======================
# Display Config
# ======================
echo "==================================="
echo " Mode        : $MODE"
echo " Users       : $USERS"
echo " Spawn Rate  : $SPAWN_RATE"
echo " Run Time    : $RUN_TIME"
echo " Profile     : $PROFILE"

if [ "$MODE" != "worker" ]; then
    echo " Report Dir  : $REPORT_DIR"
fi

echo "==================================="

# ======================
# Local Mode
# ======================
if [ "$MODE" = "local" ]; then

    mkdir -p "$REPORT_DIR"

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
# Master Mode
# ======================
elif [ "$MODE" = "master" ]; then

    mkdir -p "$REPORT_DIR"

    TEST_PROFILE=$PROFILE py -m locust \
      -f locustfile.py \
      --master \
      --expect-workers "$EXPECT_WORKERS" \
      --host="$HOST" \
      --users "$USERS" \
      --spawn-rate "$SPAWN_RATE" \
      --run-time "$RUN_TIME" \
      --headless \
      --html "$REPORT_DIR/report.html" \
      --csv "$REPORT_DIR/result"

# ======================
# Worker Mode
# ======================
elif [ "$MODE" = "worker" ]; then

    TEST_PROFILE=$PROFILE py -m locust \
      -f locustfile.py \
      --worker \
      --master-host "$MASTER_HOST"

else

    echo "Invalid MODE: $MODE"
    exit 1

fi

# ======================
# Finish
# ======================
echo ""
echo "==================================="

if [ "$MODE" = "worker" ]; then
    echo " Worker Finished"
else
    echo " Report saved to:"
    echo " $REPORT_DIR"
fi

echo "==================================="