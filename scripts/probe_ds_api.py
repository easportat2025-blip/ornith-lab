# -*- coding: utf-8 -*-
"""
probe_ds_api.py - doi moi endpoint doi dataset (public/private) va metadata.

In ma cho tung (path, method): 404 = sai path, 405 = sai method (path DUNG),
400/403 = endpoint ton tai nhung body/token sai -> can dung body.
ASCII-only. KHONG ghi key vao file.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

HOST = "https://www.kaggle.com/api"
OWNER = "khoadangnguye"
SLUG = "ornith-gui-traj"


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def key():
    return os.environ.get("KAGGLE_KEY") or hkcu("KAGGLE_KEY_A") or hkcu("KAGGLE_KEY")


def req(path, method, body):
    url = HOST + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    r.add_header("Cookie", "Kaggle_ApiKey=%s" % key())
    r.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)[:80]


PATHS = [
    "/v1/datasets/%s/%s" % (OWNER, SLUG),
    "/v1/datasets/%s/%s/visibility" % (OWNER, SLUG),
    "/v1/datasets/view/%s/%s" % (OWNER, SLUG),
    "/i/datasets.DatasetService/UpdateDatasetMetadata",
    "/i/datasets.DatasetService/EditDatasetMetadata",
    "/i/datasets.DatasetService/DatasetEditMetadata",
    "/i/datasets.DatasetService/SetDatasetVisibility",
    "/i/datasets.DatasetService/ToggleDatasetVisibility",
    "/i/datasets.DatasetService/DatasetsSetVisibility",
    "/i/datasets.DatasetService/SetDatasetPrivate",
    "/i/datasets.DatasetService/DatasetSetPublic",
    "/i/datasets.DatasetService/GetDataset",
    "/i/datasets.DatasetService/DatasetView",
]
BODIES = [
    {"datasetSlug": "%s/%s" % (OWNER, SLUG), "isPrivate": False},
    {"ownerSlug": OWNER, "datasetSlug": SLUG, "isPrivate": False},
    {"id": 1, "isPrivate": False},
]


def main():
    print("== GET/POST/PUT/PATCH voi body mac dinh ==")
    hits = []
    for p in PATHS:
        for m in ("GET", "POST", "PUT", "PATCH"):
            body = BODIES[0] if m in ("POST", "PUT", "PATCH") else None
            code, txt = req(p, m, body)
            if code != 404:
                print("  %-6s %-56s -> %s  %s" % (m, p, code,
                                                (txt or "")[:110].replace("\n", " ")))
                hits.append((p, m))
    print("\ntong hit:", len(hits))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
