# -*- coding: utf-8 -*-
"""
hf_host_data.py - host dataset .zip tren HF DATASET REPO PUBLIC de may Colab
tai bang wget/khong can token (Space tinh thi private -> 401).

Vi du tren Colab:
    wget -q https://huggingface.co/datasets/<repo>/resolve/main/<file>.zip

Dung:
    python scripts/hf_host_data.py <repo> <file1> [file2 ...]
    python scripts/hf_host_data.py --repo <repo> --stage-dir <dir>
ASCII-only source. Token doc tu HKCU (KHONG ghi key vao file).
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def tokens():
    return [t for t in (os.environ.get("HF_TOKEN"), hkcu("HF_TOKEN"),
                         os.environ.get("HF_TOKEN_2"), hkcu("HF_TOKEN_2")) if t]


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 2
    repo = None
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--repo":
            repo = args[i + 1]
            i += 2
        elif a == "--stage-dir":
            d = args[i + 1]
            for f in sorted(os.listdir(d)):
                p = os.path.join(d, f)
                if os.path.isfile(p):
                    files.append(p)
            i += 2
        else:
            files.append(a)
            i += 1
    if not repo:
        repo = os.environ.get("HF_DATA_REPO", "kkouadn/ornith-colab-data")

    from huggingface_hub import HfApi
    last = None
    for tok in tokens():
        api = HfApi(token=tok)
        try:
            api.create_repo(repo, repo_type="dataset", exist_ok=True,
                            private=False)
            print("  repo: %s (public)" % repo)
            for p in files:
                name = os.path.basename(p)
                api.upload_file(path_or_fileobj=p, path_in_repo=name,
                                repo_id=repo, repo_type="dataset",
                                commit_message="host %s" % name, token=tok)
                print("  OK  %-40s %8.2f MB" % (name,
                                               os.path.getsize(p) / 1e6))
            print("\nURL tai (wget):")
            for p in files:
                print("  https://huggingface.co/datasets/%s/resolve/main/%s"
                      % (repo, os.path.basename(p)))
            return 0
        except Exception as e:
            last = e
            print("  token 1 fail: %s" % str(e)[:120])
    print("!! het token: %s" % str(last)[:200])
    return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
