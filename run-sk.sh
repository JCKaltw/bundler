#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir pgui)/app.txt
python src/app-bundler.py $(ggdir sk) $(ggdir sk)/app.txt --no-encode
