#!/bin/bash
. ~/ggmap
. ./source-venv.sh
#  project root is $(ggdir pgdb)
ROOT_DIR=$(ggdir pgdb)

export APP_FILE="${ROOT_DIR}/app-mkdocs.txt"

export JSON_SCHEMA_FILE="${ROOT_DIR}/app-pgdb-schemas.txt"
export DDL_AST_FILE="${ROOT_DIR}/app-ddl-ast-json.txt"
export PYTHON_SCRIPTS_FILE="${ROOT_DIR}/app-pgdb-python-scripts.txt"

rm -rf ${APP_FILE}

# json schemas
python src/app-bundler.py \
    ${ROOT_DIR}/schemas \
    ${JSON_SCHEMA_FILE} \
    --no-encode \
    --extension-list json \
    --language none

# ddl-ast.json
echo "------------------------------" > ${DDL_AST_FILE}
echo "ddl-ast.json file:" >> ${DDL_AST_FILE}
echo "------------------------------" >> ${DDL_AST_FILE}
cat "${ROOT_DIR}/data/ddl-ast.json" >> ${DDL_AST_FILE}

# python scripts
python src/python_bundler.py --no-encode ${ROOT_DIR}/src ${PYTHON_SCRIPTS_FILE}

# combine them
cat ${JSON_SCHEMA_FILE} ${DDL_AST_FILE} ${PYTHON_SCRIPTS_FILE} > ${APP_FILE}
