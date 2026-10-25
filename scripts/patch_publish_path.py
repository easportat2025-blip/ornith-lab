# -*- coding: utf-8 -*-
"""
patch_publish_path.py - sua 2 loi trong publish_lora.py:
  1) fetch(): tra ve DUNG thu muc chua adapter_model.safetensors (truoc no
     them "gui_lora" vao => tra '...gui_lora\\gui_lora' => FAIL)
  2) main(): da co adapter trong thu muc tam => DUNG LAI, khong tai lai
     465MB (rat quan trong: 429 + cooldown)
ASCII-only source.
"""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
P = os.path.join(ROOT, "scripts", "publish_lora.py")

OLD_FETCH = '''    for base, _d, files in os.walk(dest):
        if "adapter_model.safetensors" in files:
            return os.path.join(base, "gui_lora")
        for f in files:
            if f == "adapter_model.safetensors":
                return base
    return None'''

NEW_FETCH = '''    for base, _d, files in os.walk(dest):
        if "adapter_model.safetensors" in files:
            return base
    return None'''

OLD_MAIN = '''    src = a.src
    if not src and a.kernel:
        tmp = os.path.join(tempfile.gettempdir(), "mimo_lora_pub_" +
                           a.kernel.replace("/", "_"))
        shutil.rmtree(tmp, ignore_errors=True)
        src = fetch(a.kernel, tmp)'''

NEW_MAIN = '''    src = a.src
    if not src and a.kernel:
        tmp = os.path.join(tempfile.gettempdir(), "mimo_lora_pub_" +
                           a.kernel.replace("/", "_"))
        # da co adapter trong thu muc tam? DUNG LAI (khong tai lai 465MB)
        src = None
        if os.path.isdir(tmp):
            for base, _d, files in os.walk(tmp):
                if "adapter_model.safetensors" in files:
                    src = base
                    print("   dung lai adapter da tai:", src)
                    break
        if not src:
            src = fetch(a.kernel, tmp)'''

s = io.open(P, encoding="utf-8", newline="").read()
if OLD_FETCH not in s:
    print("FAIL: khong tim thay fetch()")
    sys.exit(1)
if OLD_MAIN not in s:
    print("FAIL: khong tim thay main()")
    sys.exit(1)
s = s.replace(OLD_FETCH, NEW_FETCH, 1).replace(OLD_MAIN, NEW_MAIN, 1)
io.open(P, "w", encoding="utf-8", newline="").write(s)
print("da sua path + dung lai ban da tai")
