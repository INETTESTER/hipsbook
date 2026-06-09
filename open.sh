#!/bin/bash

# ======================
# Mode
# ======================
# local | master | worker
MODE="master"

# กรณี Worker
MASTER_HOST="10.0.0.1"

# กรณี Master
EXPECT_WORKERS=1

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
echo " Mode        : $MODE"
echo " Users       : $USERS"
echo " Spawn Rate  : $SPAWN_RATE"
echo " Run Time    : $RUN_TIME"
echo " Profile     : $PROFILE"
echo " Report Dir  : $REPORT_DIR"
echo "==================================="

# ======================
# Run
# ======================

if [ "$MODE" = "local" ]; then

    TEST_PROFILE=$PROFILE py -m locust \
      -f locustfile.py \
      --host="$HOST" \
      --users "$USERS" \
      --spawn-rate "$SPAWN_RATE" \
      --run-time "$RUN_TIME" \
      --headless \
      --html "$REPORT_DIR/report.html" \
      --csv "$REPORT_DIR/result"

elif [ "$MODE" = "master" ]; then

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
echo " Finished"
echo "==================================="