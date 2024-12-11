#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir pgui)/app.txt
python src/bundler.py $(ggdir pgui) $(ggdir pgui)/app.txt
