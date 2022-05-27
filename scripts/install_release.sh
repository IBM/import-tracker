#!/usr/bin/env bash

################################################################################
# This script is used to execute unit tests against a recent release without the
# code held locally. It's intended to be used inside of the `release_test`
# phase of the central Dockerfile.
################################################################################

# Make sure RELEASE_VERSION is defined
if [ -z ${RELEASE_VERSION+x} ]
then
    echo "RELEASE_VERSION must be set"
    exit 1
fi

# The name of the library we're testing
LIBRARY_NAME="import_tracker"

# 10 minutes max for trying to install the new version
MAX_DURATION="${MAX_DURATION:-600}"

# Time to wait between attempts to install the version
RETRY_SLEEP=5

# Retry the install until it succeeds
start_time=$(date +%s)
success="0"
while [ "$(expr "$(date +%s)" "-" "${start_time}" )" -lt "${MAX_DURATION}" ]
do
    pip cache purge
    pip install ${LIBRARY_NAME}==${RELEASE_VERSION}
    exit_code=$?
    if [ "$exit_code" != "0" ]
    then
        echo "Trying again in [${RETRY_SLEEP}s]"
        sleep ${RETRY_SLEEP}
    else
        success="1"
        break
    fi
done

# If the install didn't succeed, exit with failure
if [ "$success" == "0" ]
then
    echo "Unable to install [${LIBRARY_NAME}==${RELEASE_VERSION}]!"
    exit 1
fi
