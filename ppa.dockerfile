################################################################################
# This dockerfile builds a base image that can be used to validate the library
# against ubuntu PPA python builds
#
# Reference: https://github.com/IBM/import-tracker/issues/40
################################################################################

FROM ubuntu:18.04

ARG PYTHON_VERSION=3.7
RUN true && \
    apt update && \
    apt install software-properties-common -y && \
    add-apt-repository ppa:deadsnakes/ppa -y && \
    apt update && \
    apt install python${PYTHON_VERSION} python3-pip -y && \
    python${PYTHON_VERSION} -m pip install pip -U && \
    ln -s $(which python${PYTHON_VERSION}) /usr/local/bin/python && \
    ln -s $(which python${PYTHON_VERSION}) /usr/local/bin/python3 && \
    true
