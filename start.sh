#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$PROJECT_DIR/start.py" "$@"
fi

if command -v python >/dev/null 2>&1; then
    exec python "$PROJECT_DIR/start.py" "$@"
fi

printf '%s\n' '错误：未找到 Python 3.10 或更高版本。请先安装 Python。' >&2
exit 1
