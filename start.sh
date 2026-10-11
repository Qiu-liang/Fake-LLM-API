#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    SYSTEM_PYTHON=$(command -v python3 || true)
    if [ -z "$SYSTEM_PYTHON" ]; then
        printf '%s\n' '错误：未找到 python3，请先安装 Python 3.10 或更高版本。' >&2
        exit 1
    fi
    "$SYSTEM_PYTHON" -m venv "$PROJECT_DIR/.venv"
fi

if ! "$VENV_PYTHON" -c 'import fastapi, uvicorn' >/dev/null 2>&1; then
    "$VENV_PYTHON" -m pip install -e "$PROJECT_DIR"
fi

cd "$PROJECT_DIR"
exec "$VENV_PYTHON" -m fake_llm