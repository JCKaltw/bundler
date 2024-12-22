#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
rm -rf $(ggdir btc)/app.txt
python src/python_bundler.py --no-encode $(ggdir btc)/src/bktst.py $(ggdir btc)/app.txt


