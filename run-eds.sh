#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
PROJECT_ROOT="$(ggdir db)"
rm -rf "${PROJECT_ROOT}/app-eds.txt"
python src/python_bundler.py --no-encode "${PROJECT_ROOT}/src/eds.py" "${PROJECT_ROOT}/app-eds.txt"


