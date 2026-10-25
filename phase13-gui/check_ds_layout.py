"""check_ds_layout.py - kiem tra layout dataset gui-selfplay tren Kaggle."""
import re
import subprocess

p = subprocess.run(["kaggle", "datasets", "files", "hhjiji/gui-selfplay",
                     "--page-size", "200"],
                    capture_output=True)
out = (p.stdout or b"").decode("utf-8", "replace")
lines = [l for l in out.splitlines() if l.strip()]
rows = []
for l in lines[2:]:
    m = re.match(r"\s*(\S+)\s+(\d+)\s", l)
    if m:
        rows.append(m.group(1))
print("n files:", len(rows))
single = [r for r in rows if r.startswith("shots/") and r.count("/") == 1]
double = [r for r in rows if r.count("/") >= 2]
other = [r for r in rows if not r.startswith("shots/")]
print("shots/xxx.png (1 cap):", len(single), single[:3])
print("shots/shots/... (2 cap):", len(double), double[:2])
print("khac:", other[:6])
