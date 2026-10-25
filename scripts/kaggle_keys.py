"""kaggle_keys.py - doc key Kaggle tu HKCU\\Environment / env (KHONG ghi key vao file).

Dung (trong script khac, cung thu muc scripts/):
    from kaggle_keys import kaggle_env
    user, key = kaggle_env("A")      # A = khoadangnguye, B = dieniw, C = hhjiji
    if not key:
        raise SystemExit("thieu KAGGLE_KEY_A trong HKCU\\Environment")

Chu y: key chi DUOC DOC tu env/registry, khong bao gio in ra file nao.
"""
import os

ACC_USER = {"A": "khoadangnguye", "B": "dieniw", "C": "hhjiji"}
KEY_ENV = {"A": "KAGGLE_KEY_A", "B": "KAGGLE_KEY_B", "C": "KAGGLE_KEY"}


def read_key(env_name):
    """Doc gia tri tu HKCU\\Environment (Windows registry) truoc, fallback env."""
    try:
        import winreg
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        try:
            return winreg.QueryValueEx(reg, env_name)[0]
        finally:
            winreg.CloseKey(reg)
    except Exception:
        return os.environ.get(env_name)


def kaggle_env(acc):
    """Tra ve (username, key) cho acc A/B/C - key lay tu env, khong hardcode."""
    acc = str(acc).upper()
    user = ACC_USER.get(acc)
    key = read_key(KEY_ENV.get(acc, ""))
    if not (user and key):
        return None, None
    return user, key
