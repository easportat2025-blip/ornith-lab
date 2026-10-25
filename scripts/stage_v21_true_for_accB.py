# -*- coding: utf-8 -*-
"""
stage_v21_true_for_accB.py - chuan bi staging de upload adapter v21 THAT
(byte-identical voi acc A) sang acc B.

LY DO (22/10, @MiMo): hash 4 adapter tren Kaggle:
    accA khoadangnguye/ornith-gui-lora-v21 = 00d69ccc6047dbf9  (v21 THAT)
    accB dieniw/ornith-gui-lora              = f544a3bf5c7d8891  (adapter CU)
    accB dieniw/ornith-gui-lora-v21          = 8c3cb39b7efce10c  (KHAC!)
    local out_sft_v21/gui_lora                = 00d69ccc6047dbf9  (= acc A)
=> de do o (v21, task MOI) tren acc B ma so sanh duoc voi o (v21, task CU)
 tren acc A (5,6%), adapter phai BYTE GIONG => upload ban 00d69ccc...

Dung:
    python scripts/stage_v21_true_for_accB.py
    python scripts/upload_staging.py phase13-gui/lora_v21_true_accB --acc B
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
SRC = os.path.join(ROOT, "phase13-gui", "out_sft_v21", "gui_lora")
DST = os.path.join(ROOT, "phase13-gui", "lora_v21_true_accB")
SLUG = "ornith-gui-lora-v21accA"
FILES = ["adapter_config.json", "adapter_model.safetensors",
         "chat_template.jinja", "processor_config.json", "README.md",
         "tokenizer.json", "tokenizer_config.json"]


def main():
    if not os.path.isdir(SRC):
        print("FAIL: thieu nguon:", SRC)
        return 1
    os.makedirs(DST, exist_ok=True)
    missing = []
    for f in FILES:
        s = os.path.join(SRC, f)
        if not os.path.isfile(s):
            missing.append(f)
            continue
        d = os.path.join(DST, f)
        if (not os.path.exists(d)) or os.path.getsize(d) != os.path.getsize(s):
            shutil.copy2(s, d)
        print("  %-28s %d byte" % (f, os.path.getsize(d)))
    if missing:
        print("FAIL: thieu file:", missing)
        return 1
    meta = {
        "title": "Ornith GUI LoRA v21 (adapter goc acc A - byte-identical)",
        "id": "dieniw/%s" % SLUG,
        "licenses": [{"name": "other"}],
    }
    with io.open(os.path.join(DST, "dataset-metadata.json"), "w",
                 encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("staging: %s" % DST)
    print("id     : dieniw/%s" % SLUG)
    print("=> lenh upload: python scripts/upload_staging.py "
          "phase13-gui/lora_v21_true_accB --acc B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
