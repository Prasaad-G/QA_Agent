"""Helper script to package QA Agent as a standalone single-file executable."""

import os
import subprocess
import sys


def build_executable():
    print("Checking for PyInstaller...")
    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    print("Building standalone executable with PyInstaller...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=qa-agent",
        "--onedir",
        "--noconfirm",
        "--add-data=qa_agent/server/static;qa_agent/server/static",
        "main.py",
    ]

    subprocess.check_call(cmd)
    print("\nExecutable built successfully!")
    print("Binary located at: dist/qa-agent/qa-agent.exe")


if __name__ == "__main__":
    build_executable()

