#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir pgis)/app.txt
python src/bundler.py $(ggdir pgis) $(ggdir pgis)/app.txt
