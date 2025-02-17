#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
PROJECT_ROOT="$(ggdir db)"
rm -rf "${PROJECT_ROOT}/app-eds.txt"
rm -rf "${PROJECT_ROOT}/app-get-dd.txt"
python src/python_bundler.py --no-encode "${PROJECT_ROOT}/src/eds.py" "${PROJECT_ROOT}/app-eds.txt"

python src/python_bundler.py --no-encode "${PROJECT_ROOT}/src/get-dd.py" "${PROJECT_ROOT}/app-get-dd.txt"

echo "

get-dd.py project:
" >> "${PROJECT_ROOT}/app-eds.txt"

cat "${PROJECT_ROOT}/app-get-dd.txt" >> "${PROJECT_ROOT}/app-eds.txt"
