"""fix_scripts_accA.py - doi 'hhjiji/' -> 'khoadangnguye/' trong cac script
PS/py (post-action, upload) de pipeline chay dung acc A.

Chi doi o noi LA ID kaggle (khong doi comment/vi du).
"""
import io
import os
import re

FILES = [
    'scripts/after_rollout_v20.ps1',
    'scripts/after_rollout_v21.ps1',
    'scripts/post_v21_adapter.ps1',
    'scripts/post_v22_adapter.ps1',
    'scripts/post_v20_adapter.ps1',
    'scripts/upload_bench_v155.ps1',
    'scripts/upload_selfplay.ps1',
    'scripts/upload_dataset.ps1',
    'scripts/after_rollout.ps1',
]
# pattern: chuoi 'hhjiji/<slug>' (trong lenh lenh, khong phai comment dau dong)
PAT = re.compile(r'(?<![A-Za-z0-9_])hhjiji/(ornith[-\w]*|gui[-\w]*)')

n = 0
for f in FILES:
    if not os.path.exists(f):
        continue
    s = io.open(f, encoding='utf-8').read()
    out_lines = []
    changed = 0
    for ln in s.split('\n'):
        stripped = ln.lstrip()
        # giu nguyen dong comment (bat dau bang #)
        if stripped.startswith('#'):
            out_lines.append(ln)
            continue
        new = PAT.sub(r'khoadangnguye/\1', ln)
        if new != ln:
            changed += 1
        out_lines.append(new)
    if changed:
        io.open(f, 'w', encoding='utf-8', newline='').write('\n'.join(out_lines))
        print('patched %-34s (%d dong)' % (f, changed))
        n += changed
print('tong dong doi:', n)
