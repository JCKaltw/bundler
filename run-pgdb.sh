#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir pgdb)
ROOT_DIR=$(ggdir pgdb)
rm -rf ${ROOT_DIR}/app-pgdb.txt
python src/python_bundler.py --no-encode ${ROOT_DIR}/src ${ROOT_DIR}/app-pgdb.txt
