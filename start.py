from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def main() -> int:
    if sys.version_info < (3, 10):
        print("错误：需要 Python 3.10 或更高版本。", file=sys.stderr)
        return 1

    python = venv_python()
    if not python.exists():
        print("正在创建虚拟环境…")
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)

    dependencies_ready = subprocess.run(
        [str(python), "-c", "import fastapi, uvicorn"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0

    if not dependencies_ready:
        print("正在安装项目及依赖…")
        subprocess.run(
            [str(python), "-m", "pip", "install", "-e", str(PROJECT_DIR)],
            cwd=PROJECT_DIR,
            check=True,
        )

    print("正在启动 Fake LLM…")
    return subprocess.run(
        [str(python), "-m", "fake_llm", *sys.argv[1:]],
        cwd=PROJECT_DIR,
        check=False,
    ).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.returncode) from error
