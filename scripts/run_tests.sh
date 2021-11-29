#!/usr/bin/env bash

set -e
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

FAIL_THRESH=40.0
PYTHONPATH="${BASE_DIR}/src" python3 -m pytest \
    --cov-config=.coveragerc \
    --cov=src \
    --cov-report=term \
    --cov-report=html \
    --cov-fail-under=$FAIL_THRESH \
    -W error "$@"
