## Base ########################################################################
#
# This phase sets up dependencies for the other phases
##
ARG PYTHON_VERSION=3.7
ARG BASE_IMAGE=python:${PYTHON_VERSION}-slim
FROM ${BASE_IMAGE} as base

# This image is only for building, so we run as root
WORKDIR /src

# Install build, test, andn publish dependencies
COPY requirements_test.txt /src/
RUN true && \
    apt-get update -y && \
    apt-get install make git -y && \
    apt-get clean autoclean && \
    apt-get autoremove --yes && \
    pip install pip --upgrade && \
    pip install twine pre-commit && \
    pip install -r /src/requirements_test.txt && \
    true

## Test ########################################################################
#
# This phase runs the unit tests for the library
##
FROM base as test
COPY . /src
ARG RUN_FMT="true"
RUN true && \
    ./scripts/run_tests.sh && \
    RELEASE_DRY_RUN=true RELEASE_VERSION=0.0.0 \
        ./scripts/publish.sh && \
    ./scripts/fmt.sh && \
    true

## Release #####################################################################
#
# This phase builds the release and publishes it to pypi
##
FROM test as release
ARG PYPI_TOKEN
ARG RELEASE_VERSION
ARG RELEASE_DRY_RUN
RUN ./scripts/publish.sh

## Release Test ################################################################
#
# This phase installs the indicated version from PyPi and runs the unit tests
# against the installed version.
##
FROM base as release_test
ARG RELEASE_VERSION
ARG RELEASE_DRY_RUN
COPY ./test /src/test
COPY ./scripts/run_tests.sh /src/scripts/run_tests.sh
COPY ./scripts/install_release.sh /src/scripts/install_release.sh
RUN true && \
    ./scripts/install_release.sh && \
    ./scripts/run_tests.sh && \
    true
