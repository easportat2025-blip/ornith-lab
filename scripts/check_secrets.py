# -*- coding: utf-8 -*-
"""Print set/missing for runtime secrets without revealing values."""
import os
import subprocess
import sys

NAMES = [
    "KAGGLE_USERNAME", "KAGGLE_KEY", "KAGGLE_KEY_A", "KAGGLE_KEY_B",
    "HF_TOKEN", "GEMINI_API_KEY", "MISTRAL_API_KEY", "GH_TOKEN",
]


def user_env(name):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _ = winreg.QueryValueEx(k, name)
            return str(v)
    except Exception:
        return ""


def main():
    for name in NAMES:
        v = os.environ.get(name, "") or user_env(name)
        print("%-20s %-8s len=%d" % (name, "set" if v else "missing", len(v)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
