"""make_selftest_kernel.py - tao kernel CPU self-test cho B15.5 + B16-A.

Kaggle CHI upload code_file -> dummy actions duoc EMBED vao script (json string).
"""
import io
import json
import os

DST = 'phase13-gui/kernel_suite_selftest'
SRC_SCRIPT = os.path.join(DST, 'selftest_suites.py')
os.makedirs(DST, exist_ok=True)

A155 = io.open('phase13-gui/bench_v15/tasks_v15_5/dummy_actions_v155.json',
               encoding='utf-8').read()
A16 = io.open('phase13-gui/bench_v15/tasks_v16_a/dummy_actions_v16.json',
              encoding='utf-8').read()
s = io.open(SRC_SCRIPT, encoding='utf-8').read()
if "ACTIONS = {}" in s:
    old = "ACTIONS = {}"
    new = ('ACTIONS = {\n'
           '    "dummy_actions_v155.json": %s,\n'
           '    "dummy_actions_v16.json": %s,\n'
           '}' % (json.dumps(A155), json.dumps(A16)))
    s = s.replace(old, new)
    io.open(SRC_SCRIPT, 'w', encoding='utf-8').write(s)
    print('embedded actions: b155=%d B, b16=%d B' % (len(A155), len(A16)))
else:
    print('actions da embedded (giu nguyen)')

md = {
    "code_file": "selftest_suites.py",
    "competition_sources": [],
    "dataset_sources": [
        "hhjiji/ornith-offline-browsers",
        "hhjiji/ornith-gui-bench-v155",
        "hhjiji/ornith-gui-bench-v16",
    ],
    "enable_gpu": False,
    "enable_internet": True,
    "enable_tpu": False,
    "id": "hhjiji/ornith-suite-selftest",
    "is_private": True,
    "kernel_sources": [],
    "kernel_type": "script",
    "language": "python",
    "model_sources": [],
    "title": "ornith-suite-selftest",
}
json.dump(md, open(os.path.join(DST, 'kernel-metadata.json'), 'w',
                   encoding='utf-8'), ensure_ascii=False, indent=2)
print('created', DST, '| id', md['id'])
