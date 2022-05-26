################################################################################
# This dockerfile builds a base image that can be used to validate the library
# against ubuntu PPA python builds
#
# Reference: https://github.com/IBM/import-tracker/issues/40
################################################################################

FROM ubuntu:18.04

ARG PYTHON_VERSION=3.7
RUN true && \
    apt-get update && \
    apt-get install software-properties-common curl -y && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt-get update && \
    DEBIAN_FRONTEND="noninteractive" apt-get install -y \
        python${PYTHON_VERSION} \
        python${PYTHON_VERSION}-distutils && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python${PYTHON_VERSION} && \
    ln -s $(which python${PYTHON_VERSION}) /usr/local/bin/python && \
    ln -s $(which python${PYTHON_VERSION}) /usr/local/bin/python3 && \
    true
