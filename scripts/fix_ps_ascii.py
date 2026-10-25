"""fix_ps_ascii.py - quet va loai ky tu non-ASCII trong file .ps1 (PowerShell
doc bang ANSI -> ky tu UTF-8 nhu em-dash lam vo string -> parse error)."""
import io
import os
import glob

BAD = 0
for p in glob.glob('scripts/*.ps1'):
    raw = io.open(p, 'rb').read()
    try:
        txt = raw.decode('utf-8')
    except UnicodeDecodeError:
        txt = raw.decode('utf-8', 'replace')
    out = []
    for ch in txt:
        if ord(ch) < 128:
            out.append(ch)
        else:
            out.append('-')
    new = ''.join(out)
    if new != txt:
        n = sum(1 for c in txt if ord(c) >= 128)
        with io.open(p, 'w', encoding='ascii', newline='') as fh:
            fh.write(new)
        print('fixed %s (%d ky tu non-ASCII)' % (p, n))
        BAD += 1
print('done, fixed files:', BAD)
