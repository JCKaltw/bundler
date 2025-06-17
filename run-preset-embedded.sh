#!/bin/bash
. ~/ggmap
. ./source-venv.sh

PROJECT_ROOT=$(ggdir pem)

# pgis-app
rm -rf $PROJECT_ROOT/app-pem.txt
python src/app-bundler.py $PROJECT_ROOT $PROJECT_ROOT/app-pem.txt --no-encode

