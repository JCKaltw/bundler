#!/bin/bash
. ~/ggmap
. ./source-venv.sh

PROJECT_DIR=$(ggdir pgui)

rm -rf $PROJECT_DIR/app-weather-enhance.txt
python src/app-bundler.py $PROJECT_DIR $PROJECT_DIR/app-weather-enhance.txt \
    --no-encode \
    --file-subset $PROJECT_DIR/subsets/weather-enhance.txt
