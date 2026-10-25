text = ("- 20/10/2026 (tietp 42): **BAI HOC KAGGLE: kernel CHI upload `code_file`** (file phu trong thu muc kernel bi BO — `/kaggle/src` chi co `script.py`). "
"Xac minh bang kernel CPU `ornith-list-files` (in cay `/kaggle/src` + `/kaggle/input`): chi co `script.py` + `__script__.ipynb`. "
"**Hieu qua nghay:** (a) **v22 se CRASH** viet thieu `gen_synth_targeted.py` -> da INLINE module vao `gui_sft_v22.py` (44KB, kiem tra khong xung dot ten: PALETTE/CW/CH/norm giong het); "
"(b) kernel CPU self-test B15.5+B16-A v1 FAIL vi thieu dummy actions -> da EMBED json vao script (v2 da push). "
"**De quy trinh verify suite trong moi truong Kaggle THAT (CPU, khong ton GPU quota):** kernel `hhjiji/ornith-suite-selftest` — chay `bench_v155.py/bench_v16.py --dummy` voi success-policy cua tung task x 3 variant; fail LOUD (exit!=0). "
"**Patch them `--no-sandbox`** vao 2 launch trong bench_v155/bench_v16 (Kaggle co the chay root) + rebuild dataset v2. "
"**Giam N_TARGETED 600 -> 250 ep** (~940 row, ~24% mix) de khong dua synth len thieu so voi data that. "
"**Queue GPU 24/10 da len 13 muc** (them bench-v22/bench-v155-v22/bench-v16-v22 + rollout-v21 vong self-play 2) + **dry-run PASS** (2 session/vong, dung dependency `after` + `needs_dataset`). "
"**V22 kernel** them `kernel_bench_v22/bench_v155_v22/bench_v16_v22` (script chung `make_bench_any.py` tao kernel bench theo (suite x adapter)).")

with open('PLAN.md', 'a', encoding='utf-8') as f:
    f.write("\n" + text)
print('appended', len(text))
