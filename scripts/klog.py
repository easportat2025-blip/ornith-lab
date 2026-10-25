# -*- coding: utf-8 -*-
"""
klog.py - doc log kernel Kaggle (JSON-lines stdout/stderr) de doc nhanh.

Log Kaggle moi co dang:
  ,{"stream_name":"stdout","time":216.9,"data":"[env] display :99: ok\\n"}

Dung:
    python scripts/klog.py <file.log> [--tail N] [--grep PAT] [--ctx N]
    python scripts/klog.py <file.log> --list      (chi danh sach dong co loi/canh bao)
ASCII-only source.
"""
import argparse
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LINE_RE = re.compile(
    r'\{"stream_name":"(?P<st>stdout|stderr)","time":(?P<t>[0-9.]+),'
    r'"data":"(?P<d>.*?)"\}', re.S)
WARN_RE = re.compile(
    r"(Traceback|Error|ERROR|FAIL|WARN|Exception|den goc|black|empty|"
    r"khong resolve|timeout|timed out|Warning)", re.I)


def parse(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    out = []
    for m in LINE_RE.finditer(raw):
        data = m.group("d")
        try:
            data = data.encode("utf-8").decode("unicode_escape", errors="replace")
        except Exception:
            pass
        out.append((float(m.group("t")), m.group("st"), data))
    if not out:
        # fallback: log khong phai JSON-lines -> in thang
        for i, line in enumerate(raw.splitlines()):
            out.append((float(i), "raw", line + "\n"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--tail", type=int, default=40)
    ap.add_argument("--grep", default="")
    ap.add_argument("--ctx", type=int, default=0)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.log):
        print("KHONG TON TAI:", a.log)
        return 1
    lines = parse(a.log)
    print("== %s : %d dong ==" % (a.log, len(lines)))
    if a.list:
        pat = re.compile(a.grep) if a.grep else WARN_RE
        n = 0
        for i, (t, st, s) in enumerate(lines):
            if pat.search(s):
                n += 1
                print("[%8.1f][%s] %s" % (t, st, s.rstrip()[:240]))
        print("-- %d dong khop" % n)
        return 0
    sel = lines
    if a.grep:
        pat = re.compile(a.grep, re.I)
        idx = set()
        for i, (t, st, s) in enumerate(lines):
            if pat.search(s):
                for j in range(max(0, i - a.ctx), min(len(lines), i + a.ctx + 1)):
                    idx.add(j)
        sel = [lines[i] for i in sorted(idx)]
    else:
        sel = lines[-a.tail:]
    for t, st, s in sel:
        print("[%8.1f][%s] %s" % (t, st, s.rstrip()[:400]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
