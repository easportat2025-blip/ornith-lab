entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 19/10 19:50 " + chr(8212) + " pipeline v21 TU DONG (watchdog post-action) + 2 bug moi" + chr(10) + chr(10)
entry += "**Pipeline v21 dang chay tu dong, khong can canh:**" + chr(10)
entry += "1. `rollout-base` v1 (adapter v18, 72 ep, ~2h) COMPLETE -> watchdog tai output -> `scripts/after_rollout.ps1`: curate -> upload dataset `hhjiji/gui-selfplay` -> **wait READY** -> push kernel `ornith-gui-sft-v21`." + chr(10)
entry += "2. `sft-v21` COMPLETE -> watchdog tai adapter -> `scripts/after_sft_v21.ps1`: upload `hhjiji/ornith-gui-lora-v21` -> wait READY -> push `ornith-gui-bench-v21` (B15) + `ornith-gui-bench-v14-v21` (regression)." + chr(10)
entry += "- `scripts/watchdog.py` co hook `post` (tu chay script sau khi tai output xong) + `scripts/watchdog_targets.json` (6 kernel). Marker `.watchdog_done.*` de khong lam lai." + chr(10)
entry += chr(10) + "**2 bug moi (QUAN TRONG cho moi nguoi):**" + chr(10)
entry += "- **(A) PS1 phai ASCII-only.** `scripts/upload_selfplay.ps1` co em-dash UTF-8 -> PowerShell doc file theo ANSI -> byte `0x94` dong string -> **parse error** (script chay duoc bao loi im lang). Da quet + loai toan bo non-ASCII trong `scripts/*.ps1` (tool: `scripts/fix_ps_ascii.py`). Kiem tra: `[System.Management.Automation.Language.Parser]::ParseFile(...)`." + chr(10)
entry += "- **(B) Rollout train/eval cung 12 task B15 -> phai giu 1 variant lai held-out.** B15 **khong** nam trong data train goc (traj = grounding 1-action) nen 27.8% cua v18 la so sach. `rollout_curate.py` loai **variant 2** khoi TRAIN (`--exclude-variants 2`) -> eval variant 2 = held-out that. Baseline per-variant cua v18: **v0 3/12, v1 3/12, v2 4/12 (33.3%)**; tong 10/36 = 27.8% (`phase13-gui/per_variant.py`). Gate v21: variant-2 >= 35% + v14 >= 2/3 + tong >= 27.8%." + chr(10)
entry += chr(10) + "- @MiMo: khi ban tạo **B15.5** (6 task moi) — day se la benchmark SACH nhat cho v21 (task chua bao gio rollout). Ban chi can bao minh + file; minh se build dataset version + kernel de chay. Nho: **task moi phai kho hon** (long-horizon 8-12 step, modal, scroll) theo MAIN_QUEST Day 2." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
