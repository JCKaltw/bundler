#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir dash)/app.txt
python src/app-bundler.py $(ggdir dash) $(ggdir dash)/app.txt --no-encode
