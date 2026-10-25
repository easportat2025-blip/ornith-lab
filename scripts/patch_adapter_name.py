# -*- coding: utf-8 -*-
"""
patch_adapter_name.py - (1) make_desktop_bench.py: khai bao ADAPTER_NAME 1 cho
(2) make_desktop_bench_split.py: doi ADAPTER_NAME theo tung split
=> kernel desktop khong con "code doi adapter, metadata doi adapter" (nguyen
do b3 chet: mount lora-v22 nhung require_datasets doi lora-v21).

ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
B = os.path.join(ROOT, "phase13-gui", "make_desktop_bench.py")
S = os.path.join(ROOT, "phase13-gui", "make_desktop_bench_split.py")

# 1) builder: hardcode -> bien
OLD_CALL = '''        require_datasets(["ornith-gui-lora-v21", "ornith-offline-browsers",
                          "ornbase-s1", "ornbase-s2", "ornbase-s3", "ornbase-s4"])'''
NEW_CALL = '''        require_datasets([ADAPTER_NAME, "ornith-offline-browsers",
                          "ornbase-s1", "ornbase-s2", "ornbase-s3", "ornbase-s4"])'''

# them bien ADAPTER_NAME canh code vao DRIVER (truoc TASK_TABLE)
OLD_DECL = "TASK_TABLE = {"
NEW_DECL = ('# FIX 22/10 (MiMo): adapter dung phai khai bao 1 cho - tranh\n'
            '# xung dot "code doi adapter" vs "metadata doi adapter"\n'
            '# (kernel b3 chet: mount lora-v22 nhung require_datasets doi lora-v21)\n'
            'ADAPTER_NAME = "ornith-gui-lora-v21"\n'
            '\n'
            'TASK_TABLE = {')

s = io.open(B, encoding="utf-8", newline="").read()
if "ADAPTER_NAME" in s:
    print("builder: da co ADAPTER_NAME -> bo qua")
else:
    if OLD_CALL not in s:
        print("FAIL: khong tim thay require_datasets call")
        sys.exit(1)
    s = s.replace(OLD_CALL, NEW_CALL, 1)
    if OLD_DECL not in s:
        print("FAIL: khong tim thay TASK_TABLE de chen bien")
        sys.exit(1)
    s = s.replace(OLD_DECL, NEW_DECL, 1)
    io.open(B, "w", encoding="utf-8", newline="").write(s)
    print("da sua builder:", B)

# 2) split builder: doi ADAPTER_NAME theo split
OLD_SWAP = '''SWAP = {'''
NEW_SWAP = '''# FIX 22/10 (MiMo): adapter dung theo tung split (b3 = v22, b = v21)
ADAPTER_BY_TAG = {"a": "ornith-gui-lora-v21",
                  "b": "ornith-gui-lora-v21",
                  "b3": "ornith-gui-lora-v22"}

SWAP = {'''

t = io.open(S, encoding="utf-8", newline="").read()
if "ADAPTER_BY_TAG" in t:
    print("split: da co ADAPTER_BY_TAG -> bo qua")
else:
    if OLD_SWAP not in t:
        print("FAIL: khong tim thay SWAP trong split builder")
        sys.exit(1)
    t = t.replace(OLD_SWAP, NEW_SWAP, 1)
    # patch ADAPTER_NAME trong source sinh ra
    anchor = '''    # verify app files co trong source moi (guard fail-loud cua kernel)'''
    patch = '''    # FIX 22/10 (MiMo): doi ADAPTER_NAME cho khop adapter ma split mount
    _ad = ADAPTER_BY_TAG.get(tag, "ornith-gui-lora-v21")
    src = src.replace('ADAPTER_NAME = "ornith-gui-lora-v21"',
                      'ADAPTER_NAME = "%s"' % _ad)
    print("   adapter: %s" % _ad)
''' + anchor
    if anchor not in t:
        print("FAIL: khong tim thay anchor verify-app trong split builder")
        sys.exit(1)
    t = t.replace(anchor, patch, 1)
    io.open(S, "w", encoding="utf-8", newline="").write(t)
    print("da sua split builder:", S)
print("OK")
