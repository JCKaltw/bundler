#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
rm -rf $(ggdir btc)/app-tdr.txt
python src/python_bundler.py --no-encode $(ggdir btc)/src/tdr.py $(ggdir btc)/app-tdr.txt


