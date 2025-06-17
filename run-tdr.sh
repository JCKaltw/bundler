#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
ROOTDIR=$(ggdir btc)
rm -rf ${ROOTDIR}/app-tdr.txt
python src/python_bundler.py --no-encode \
    ${ROOTDIR}/src/tdr.py \
    ${ROOTDIR}/app-tdr.txt


