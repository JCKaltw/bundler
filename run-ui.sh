#!/bin/bash
. ~/ggmap
. ./source-venv.sh
rm -rf $(ggdir ui)/app.txt
python src/node_bundler.py $(ggdir ui) $(ggdir ui)/app.txt
