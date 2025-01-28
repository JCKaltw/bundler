#!/bin/bash
. ~/ggmap
. ./source-venv.sh

PROJECT_ROOT=$(ggdir pgis)

# pgis-app
rm -rf $PROJECT_ROOT/pgis-app.txt
python src/app-bundler.py $PROJECT_ROOT $PROJECT_ROOT/pgis-app.txt --no-encode

# pgis-data
rm -rf $PROJECT_ROOT/pgis-data.txt
python src/app-bundler.py $PROJECT_ROOT/data $PROJECT_ROOT/pgis-data.txt \
  --language none --extension-list "json" --no-encode
