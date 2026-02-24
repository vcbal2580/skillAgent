import sys
import subprocess


def main():
    """hi vcbal 命令入口"""
    python_path = r"F:\aiagent\.venv\Scripts\python.exe"
    main_path = r"F:\aiagent\main.py"

    # 透传参数，比如 hi vcbal server → 启动 server 模式
    args = sys.argv[1:]

    # 如果通过 "hi vcbal" 调用，去掉 "vcbal"
    if args and args[0] == "vcbal":
        args = args[1:]

    try:
        subprocess.run([python_path, main_path] + args)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
