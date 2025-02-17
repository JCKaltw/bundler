#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
ROOTDIR=$(ggdir btc)
rm -rf ${ROOTDIR}/app-bktst-tdr.txt
python src/python_bundler.py --no-encode \
    ${ROOTDIR}/src/bktst.py ${ROOTDIR}/src/tdr.py \
    ${ROOTDIR}/app-bktst-tdr.txt


