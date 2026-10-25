"""patch_suite_nosandbox.py - them --no-sandbox vao cac launch trong bench_v155/v16.

Kaggle kernel chay voi quyen root -> chromium launch KHONG co --no-sandbox se
fail ("Running as root without --no-sandbox is not supported") -> toan bo suite
fail 0/18. Bench kernel cua ta (kernel_bench_*) co --no-sandbox, nhung suite
tu chay browser NOI BO (bench_v155.run_suite / get_spec) thi khong.
"""
import os
import re

TARGETS = ['phase13-gui/bench_v15/tasks_v15_5/bench_v155.py',
           'phase13-gui/bench_v15/tasks_v16_a/bench_v16.py']
PAT = re.compile(r'\.launch\(headless=True\)')
REP = '.launch(headless=True, args=["--no-sandbox"])'

for p in TARGETS:
    if not os.path.exists(p):
        print('skip (khong co)', p)
        continue
    s = open(p, encoding='utf-8').read()
    n = len(PAT.findall(s))
    if n == 0:
        print('khong can patch', p)
        continue
    s = PAT.sub(REP, s)
    open(p, 'w', encoding='utf-8').write(s)
    print('patched %s: %d launch -> them --no-sandbox' % (p, n))
print('done')
