#!/bin/bash
. ~/ggmap
. ./source-venv.sh
ROOT_DIR=$(ggdir tdrv)
export APP_FILE="${ROOT_DIR}/app-tdrv.txt"

echo "Starting script..."
echo "ROOT_DIR: ${ROOT_DIR}"
echo "APP_FILE: ${APP_FILE}"

rm -rf ${APP_FILE}

python src/app-bundler.py ${APP_FILE} \
        --no-encode --extension-list=js,json --language=none \
        ${ROOT_DIR}
