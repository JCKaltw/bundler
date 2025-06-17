#!/bin/bash
. ~/ggmap
. ./source-venv.sh
# project root is $(ggdir btc)
ROOTDIR=$(ggdir pgdb)
rm -rf ${ROOTDIR}/app-pgdb-changes.txt
python src/python_bundler.py --no-encode \
    ${ROOTDIR}/src/apply-ddl-changes.py ${ROOTDIR}/src/apply-dml-changes.py \
    ${ROOTDIR}/app-pgdb-changes.txt


