#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir ui)/app.txt
python src/app-bundler.py $(ggdir ui) $(ggdir ui)/app.txt
