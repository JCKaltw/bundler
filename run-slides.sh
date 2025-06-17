#!/bin/bash
. ~/ggmap
. ./source-venv.sh
PROJECT_ROOT="$(ggdir slides)"
rm -rf $(ggdir pgui)/app.txt

python src/app-bundler.py $PROJECT_ROOT $PROJECT_ROOT/app.txt --no-encode --root-files='next.config.js' --include-patterns public/*.html
