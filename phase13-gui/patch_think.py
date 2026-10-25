"""patch_think.py - them co ENABLE_THINKING vao bench/rollout kernel.

Ly do: chat template ho tro `enable_thinking=False` -> render think RONG
("<think>\\n\\n</think>\\n\\n") -> model (train action-only) emit thang action,
khong con prose -> het fail mode C1 (prose/no-action) + giai phong budget 256.

Mac dinh GIU NGUYEN (ENABLE_THINKING=True) de so sanh duoc voi baseline 27.8%
(do voi thinking ON). Bien thep think0 = kernel rieng.
"""
import os

BENCH = ['phase13-gui/kernel_bench_v15/bench_v15_kernel.py']
ROLL = ['phase13-gui/kernel_rollout_v20/rollout_kernel.py',
        'phase13-gui/kernel_rollout_base/rollout_kernel.py']

CONST = '''
# --- ENABLE_THINKING: prompt co render think rong (enable_thinking=False) thi
# model (train action-only) emit thang action, het prose leak (failure C1).
# Mac dinh True de so sanh duoc voi baseline B15 27.8% (do voi thinking ON).
ENABLE_THINKING = os.environ.get("ORNI_THINK", "1") != "0"
'''

OLD_CALL = """            msgs, tokenize=False, add_generation_prompt=True)"""
NEW_CALL = """            msgs, tokenize=False, add_generation_prompt=True,
            enable_thinking=ENABLE_THINKING)"""

OLD_CALL2 = """                msgs, tokenize=False, add_generation_prompt=True)"""
NEW_CALL2 = """                msgs, tokenize=False, add_generation_prompt=True,
                enable_thinking=ENABLE_THINKING)"""


def patch(path):
    s = open(path, encoding='utf-8').read()
    if 'ENABLE_THINKING' in s:
        print('skip (da patch)', path)
        return
    n = 0
    for old, new in ((OLD_CALL, NEW_CALL), (OLD_CALL2, NEW_CALL2)):
        if old in s:
            s = s.replace(old, new)
            n += 1
    # them constant sau khi import os (dong import dau tien co os)
    lines = s.split('\n')
    for i, ln in enumerate(lines):
        if ln.strip() == 'import os' or ln.startswith('import os,'):
            lines.insert(i + 1, CONST)
            break
    else:
        for i, ln in enumerate(lines):
            if ln.startswith('import '):
                lines.insert(i + 1, CONST)
                break
    s = '\n'.join(lines)
    open(path, 'w', encoding='utf-8').write(s)
    print('patched', path, '| call sites patched:', n)


for p in BENCH + ROLL:
    if os.path.exists(p):
        patch(p)
print('done')
