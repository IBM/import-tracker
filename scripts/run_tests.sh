#!/usr/bin/env bash

set -e
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

if [ "$PARALLEL" == "1" ]
then
    procs=${NPROCS:-$(nproc)}
    echo "Running tests in parallel with [$procs] workers"
    procs_arg="-n $procs"
else
    echo "Running tests in serial"
    procs_arg=""
fi

FAIL_THRESH=100.0
python3 -m pytest \
    $procs_arg \
    --cov-config=.coveragerc \
    --cov=import_tracker \
    --cov-report=term \
    --cov-report=html \
    --cov-fail-under=$FAIL_THRESH \
    --asyncio-mode=strict \
    -W error "$@"
