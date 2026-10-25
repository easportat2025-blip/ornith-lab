# -*- coding: utf-8 -*-
"""
ds_visibility.py - xem / doi public<->private cho dataset Kaggle (acc A).

CLI khong co lenh doi visibility -> dung API noi bo / v1.
Thu nhieu endpoint + body shape, in ket qua tung thu (de biet endpoint nao
dung) - KHONG ghi key vao file.

Usage:
    python scripts/ds_visibility.py list khoadangnguye/ornith-gui-traj
    python scripts/ds_visibility.py public khoadangnguye/ornith-gui-traj [...]
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

HOST = "https://www.kaggle.com/api"


def hkcu(var):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            v, _t = winreg.QueryValueEx(k, var)
            return str(v).strip()
    except Exception:
        return ""


def key_of(owner):
    var = "KAGGLE_KEY_A" if owner == "khoadangnguye" else "KAGGLE_KEY_B"
    return (os.environ.get(var) or hkcu(var) or hkcu("KAGGLE_KEY") or "")


def req(url, key, method="POST", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    r.add_header("Cookie", "Kaggle_ApiKey=%s" % key)
    r.add_header("User-Agent", "Mozilla/5.0")
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return -1, str(e)


def info(slug):
    owner, name = slug.split("/")
    key = key_of(owner)
    code, txt = req("%s/v1/datasets/view/%s/%s" % (HOST, owner, name), key,
                    method="GET")
    if code != 200:
        return {"error": txt[:120]}
    try:
        d = json.loads(txt)
    except Exception:
        return {"error": txt[:120]}
    return {"isPrivate": d.get("isPrivate"), "title": d.get("title"),
            "totalBytes": d.get("totalBytes") or d.get("datasetFilesSize"),
            "ref": d.get("ref")}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    mode = sys.argv[1]
    slugs = sys.argv[2:]
    if mode == "list":
        for s in slugs:
            print("  %-46s %s" % (s, json.dumps(info(s), ensure_ascii=False)))
        return 0
    # doi public
    for s in slugs:
        owner, name = s.split("/")
        key = key_of(owner)
        cands = [
            ("i/DatasetSetPrivate",
             "%s/i/datasets.DatasetService/DatasetSetPrivate" % HOST,
             {"datasetSlug": s, "isPrivate": False}),
            ("i/UpdateDataset",
             "%s/i/datasets.DatasetService/UpdateDataset" % HOST,
             {"datasetSlug": s, "isPrivate": False}),
            ("i/DatasetSetVisibility",
             "%s/i/datasets.DatasetService/DatasetSetVisibility" % HOST,
             {"datasetSlug": s, "visibility": "PUBLIC"}),
            ("v1/visibility",
             "%s/v1/datasets/%s/%s/visibility" % (HOST, owner, name),
             {"isPrivate": False}),
        ]
        done = False
        for tag, url, body in cands:
            code, txt = req(url, key, body=body)
            ok = code == 200
            print("  %-42s %-22s -> %s %s" % (s, tag, code,
                                              (txt or "")[:90].replace("\n", " ")))
            if ok:
                done = True
                break
        if not done:
            print("     (khong endpoint nao OK cho %s)" % s)
        else:
            print("     -> kiểm tra:", json.dumps(info(s), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
