#!/bin/bash
python_versions="3.7 3.8 3.9 3.10"
GREEN='\033[0;32m'
NC='\033[0m'

for python_version in $python_versions; do
    echo -e "${GREEN}Building wheel for Python version [${python_version}]${NC}"
    PYTHON_RELEASE_VERSION=$python_version python3 setup.py bdist_wheel clean --all
    echo -e "${GREEN}Done building wheel for Python version [${python_version}]${NC}"
    sleep 2
done
