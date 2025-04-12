#!/bin/bash
. ~/ggmap
. ./source-venv.sh
#  project root is $(ggdir pgdb)
ROOT_DIR=$(ggdir es2)
export APP_FILE="${ROOT_DIR}/app-mkdocs.txt"

echo "Starting script..."
echo "ROOT_DIR: ${ROOT_DIR}"
echo "APP_FILE: ${APP_FILE}"

rm -rf ${APP_FILE}

python src/app-bundler.py ${APP_FILE} \
        --no-encode --extension-list=sh,yml,yaml,json,md,txt --language=none \
       /Users/chris/projects/es2/.github/workflows \
       /Users/chris/projects/es2/infrastructure \
       /Users/chris/projects/es2/docs --tree-only \
       /Users/chris/projects/es2/docs/bin
