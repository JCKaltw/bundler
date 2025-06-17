#!/bin/bash
. ~/ggmap
. ./source-venv.sh

PROJECT_DIR=$(ggdir pgui)

rm -rf $PROJECT_DIR/app.txt
python src/app-bundler.py $PROJECT_DIR $PROJECT_DIR/app-weather.txt \
    --no-encode \
    --file-subset $PROJECT_DIR/subsets/weather-subset.txt
