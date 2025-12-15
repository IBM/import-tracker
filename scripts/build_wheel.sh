#!/bin/bash

# Version of Import Tracker that we want to tag our wheel as
release_version=${RELEASE_VERSION:-""}
# Python tags we want to support
python_versions="py37 py38 py39 py310"
GREEN='\033[0;32m'
NC='\033[0m'

function show_help
{
cat <<- EOM
Usage: scripts/build_wheels.sh -v [Import Tracker Version] -p [python versions]
EOM
}

while (($# > 0)); do
  case "$1" in
  -h | --h | --he | --hel | --help)
    show_help
    exit 2
    ;;
  -p | --python_versions)
    shift
    python_versions=""
    while [ "$#" -gt "0" ]
    do
      if [ "$python_versions" != "" ]
      then
        python_versions="$python_versions "
      fi
      python_versions="$python_versions$1"
      if [ "$#" -gt "1" ] && [[ "$2" == "-"* ]]
      then
        break
      fi
      shift
    done
    ;;
  -v | --release_version)
    shift; release_version="$1";;
  *)
    echo "Unknown argument: $1"
    show_help
    exit 2
    ;;
  esac
  shift
done

if [ "$release_version" == "" ]; then
    echo "ERROR: a release version for Import Tracker must be specified."
    show_help
    exit 1
else
    echo -e "Building wheels for Import Tracker version: ${GREEN}${release_version}${NC}"
    sleep 2
fi
for python_version in $python_versions; do
    echo -e "${GREEN}Building wheel for Python version [${python_version}]${NC}"
    RELEASE_VERSION=$release_version python3 setup.py bdist_wheel --python-tag ${python_version} clean --all
    echo -e "${GREEN}Done building wheel for Python version [${python_version}]${NC}"
    sleep 1
done
