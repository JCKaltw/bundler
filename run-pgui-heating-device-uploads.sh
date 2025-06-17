#!/bin/bash
. ~/ggmap
. ./source-venv.sh

PROJECT_DIR=$(ggdir pgui)

rm -rf $PROJECT_DIR/app-heating-device-uploads.txt

python src/app-bundler.py $PROJECT_DIR $PROJECT_DIR/app-heating-device-uploads.txt \
    --no-encode \
    --file-subset $PROJECT_DIR/subsets/heating-device-uploads.txt
