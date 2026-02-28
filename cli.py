import sys
import os
import subprocess
from pathlib import Path


def main():
    """hi vcbal 命令入口"""
    python_path = sys.executable
    main_path = Path(__file__).resolve().with_name("main.py")

    # 透传参数，比如 hi vcbal server → 启动 server 模式
    args = sys.argv[1:]

    # 如果通过 "hi vcbal" 调用，去掉 "vcbal"
    if args and args[0] == "vcbal":
        args = args[1:]

    # Force UTF-8 mode so Chinese characters in .mo/.yaml files decode correctly
    # on Windows where the default codec is often ASCII or cp1252.
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        subprocess.run([python_path, str(main_path)] + args, env=env)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
