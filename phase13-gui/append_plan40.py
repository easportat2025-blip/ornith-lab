text = ("- 19/10/2026 (tiếp 40): **B15 v18 = 10/36 (27.8%) vs v20 = 3/36 (8.3%) -> V20 REGRESSION do RECIPE.** "
"v18 (`kernel/gui_sft.py`) huan luyen 1 DONG ACTION; v20 (`kernel_v20/gui_sft_v20.py`) huan luyen `THINK:` (template `make_think`) + `ACTION:` "
"voi REASON_MAX=256. Data GIONG (synth+real-ui+gui-traj; v20 KHONG mount gui-traj-v19) -> khac biet la format/SYS, khong phai data. "
"Recipe reasoning lam model hong tren multi-step (prose an budget, loop), con single-step grounding thi v18 > v20. "
"**Quyet dinh: v21 = recipe v18 + self-play** (`kernel_v21/gui_sft_v21.py` fork tu gui_sft.py, them self-play cap 30%, steps scale; tao boi `phase13-gui/make_v21.py`). "
"**Bug rollout (0 dong du lieu):** `rollout_episode` chi giu rows cua episode WIN -> 0/9 win => 0 rows (smoke v1; `parse=0` chi vi rong). "
"Da sua: giu TAT CA step + nhan `win`/`n_fail_checks`/`n_checks`/`fail_reason`; `lora_fixed` -> /tmp (bo 465MB adapter vao output); SMOKE_TASKS=[] (full run). "
"Da push `ornith-gui-rollout-base` v1 (adapter v18, 72 ep, ~2h) + `ornith-gui-rollout-v20` v3 (adapter v20, 36 ep, ~1h). "
"Curate moi (`rollout_curate.py`): uu tien WIN, FAIL gan bo step cuoi, bo action lap, xuat `traj.jsonl` (v18 format) + `traj_reason.jsonl`. "
"**Watchdog:** `scripts/watchdog.py` (6 kernel, poll 120s, tu tai output, fix charmap) + `scripts/watch_agent_md.py` (watcher ONE-SHOT agent.md theo LUAT CUNG #4). "
"Pipeline v21 da chuan bi: `kernel_bench_v21` (id `hhjiji/ornith-gui-bench-v21`, mount `ornith-gui-lora-v21`) + `scripts/post_v21_adapter.ps1` (tai adapter -> upload dataset -> wait READY).\n")

with open('PLAN.md', 'a', encoding='utf-8') as f:
    f.write("\n" + text)
print('appended', len(text))
