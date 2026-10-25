# -*- coding: utf-8 -*-
"""
space_host_files.py - HOST FILE (dataset .zip) len Space TINH de may Colab tai
bang wget (tranh endpoint 'colab upload' cua Colab tra 500).

Vi du tren Colab:
    wget -q https://himagayem-ornith-agent.static.hf.space/data/ornith-gui-traj.zip
    unzip -q ornith-gui-traj.zip -d /content/data/ornith-gui-traj/

Dung:
    python scripts/space_host_files.py <file1> [file2 ...]
    python scripts/space_host_files.py --stage-dir <dir>   # het file trong dir
ASCII-only source. Token doc tu HKCU (KHONG ghi key vao file).
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("SPACE_REPO", "himAgayem/ornith-agent")


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def token_for_repo(repo):
    """Token dung cho repo Space nay (HF_TOKEN_2 cho acc himAgayem)."""
    if "himagayem" in repo.lower():
        return (os.environ.get("HF_TOKEN_2") or hkcu("HF_TOKEN_2")
                or os.environ.get("HF_TOKEN") or hkcu("HF_TOKEN") or "")
    return (os.environ.get("HF_TOKEN") or hkcu("HF_TOKEN") or "")


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    files = []
    if args[0] == "--stage-dir":
        d = args[1]
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if os.path.isfile(p):
                files.append(p)
    else:
        files = args
    tok = token_for_repo(REPO)
    if not tok:
        print("!! thieu token cho Space %s (HF_TOKEN_2 / HF_TOKEN)" % REPO)
        return 1
    from huggingface_hub import HfApi
    api = HfApi(token=tok)
    ok = 0
    for p in files:
        name = os.path.basename(p)
        size = os.path.getsize(p) / 1e6
        try:
            api.upload_file(path_or_fileobj=p, path_in_repo="data/" + name,
                            repo_id=REPO, repo_type="space",
                            commit_message="host %s" % name, token=tok)
            print("  OK  data/%-38s %8.2f MB" % (name, size))
            ok += 1
        except Exception as e:
            print("  FAIL data/%-38s %s" % (name, str(e)[:150]))
    print("\nURL tai (wget):")
    for p in files:
        print("  https://himagayem-ornith-agent.static.hf.space/data/"
              + os.path.basename(p))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
