# Bang nang luc (PLAN.md W2) + loi ha tang

Sinh boi `scripts/ability_table.py` (scan phase13-gui/out_*/**/*result*.json).

Cot A1..A10 = wins/ep cua tung nang luc trong file do (khong phu cover = '-'). `loi` = ep loi ha tang (man hinh den va/hoac infra_errors).

## 1. Tung file result

| file | loai | suite | adapter | n_ep | win | win% | loi | A1 | A2 | A3 | A4 | A5 | A6 | A7 | A8 | A9 | A10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| out_bench-v155-v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 18 | 10 | 55.6% | 0 | - | 0/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench-v16-v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 24 | 11 | 45.8% | 0 | 2/6 | 1/6 | - | - | - | 2/3 | - | 3/6 | - | - |
| out_bench-v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 36 | 12 | 33.3% | 0 | - | - | - | 3/3 | - | - | 0/3 | - | - | - |
| out_bench | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_bench_3d_B | 3d |  |  | 100 | 65 | 65% | 0 | - | - | - | - | - | - | - | - | 65/100 | - |
| out_bench_3d_hard_B | 3d |  |  | 100 | 5 | 5% | 0 | - | - | - | - | - | - | - | - | 5/100 | - |
| out_bench_3d_v21 | 3d |  |  | 100 | 27 | 27% | 0 | - | - | - | - | - | - | - | - | 27/100 | - |
| out_bench_v14 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_bench_v155_B | web | B15.5 | /kaggle/input/datasets/dieniw/ornith-gui-lora | 18 | 0 | 0.0% | 0 | - | 0/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v21 | web | B15.5 | /kaggle/input/datasets/khoadangnguye/ornith-gui-lora-v21 | 18 | 1 | 5.6% | 0 | - | 0/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v21new_B | web | B15.5 | /kaggle/input/ornith-gui-lora-v21 | 18 | 8 | 44.4% | 0 | - | 2/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 18 | 10 | 55.6% | 0 | - | 0/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v22_b | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 18 | 10 | 55.6% | 0 | - | 0/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v22_old_B | web | B15 | /kaggle/input/datasets/dieniw/ornith-gui-lora-v22 | 18 | 3 | 16.7% | 0 | - | 1/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v155_v24_B | web | B15 | /kaggle/input/datasets/dieniw/ornith-gui-lora-v24 | 18 | 9 | 50.0% | 0 | - | 2/3 | - | - | 0/3 | - | - | - | - | - |
| out_bench_v15 | web | B15 | /kaggle/input/datasets/hhjiji/ornith-gui-lora | 36 | 10 | 27.8% | 0 | - | - | - | 0/3 | - | - | 0/3 | - | - | - |
| out_bench_v15_v20 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_bench_v15_v4 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_bench_v16_B | web | B15 | /kaggle/input/ornith-gui-lora | 24 | 6 | 25.0% | 0 | 3/6 | 0/6 | - | - | - | 0/3 | - | 3/6 | - | - |
| out_bench_v16_v21 | web | B15 | /kaggle/input/datasets/khoadangnguye/ornith-gui-lora-v21 | 24 | 7 | 29.2% | 0 | 0/6 | 0/6 | - | - | - | 3/3 | - | 4/6 | - | - |
| out_bench_v16_v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 24 | 11 | 45.8% | 0 | 2/6 | 1/6 | - | - | - | 2/3 | - | 3/6 | - | - |
| out_bench_v16_v22b_B | web | B15 | /kaggle/input/datasets/dieniw/ornith-gui-lora-v22 | 24 | 13 | 54.2% | 0 | 2/6 | 0/6 | - | - | - | 2/3 | - | 6/6 | - | - |
| out_bench_v16_v24_B | web | B15 | /kaggle/input/ornith-gui-lora-v24 | 24 | 16 | 66.7% | 0 | 4/6 | 0/6 | - | - | - | 3/3 | - | 6/6 | - | - |
| out_bench_v18_think0 | web | B15 | /kaggle/input/ornith-gui-lora | 36 | 9 | 25.0% | 0 | - | - | - | 0/3 | - | - | 0/3 | - | - | - |
| out_bench_v21 | web | B15 | /kaggle/input/datasets/khoadangnguye/ornith-gui-lora-v21 | 36 | 11 | 30.6% | 0 | - | - | - | 0/3 | - | - | 0/3 | - | - | - |
| out_bench_v22 | web | B15 | /kaggle/input/ornith-gui-lora-v22 | 36 | 12 | 33.3% | 0 | - | - | - | 3/3 | - | - | 0/3 | - | - | - |
| out_bench_v24_B | web | B15 | /kaggle/input/ornith-gui-lora-v24 | 36 | 22 | 61.1% | 0 | - | - | - | 3/3 | - | - | 3/3 | - | - | - |
| out_desktop_bench_a/desktop_bench | desktop |  |  | 80 | 0 | 0% | 40 | - | - | - | - | - | - | - | - | - | 0/80 |
| out_desktop_bench_b2/desktop_bench | desktop |  |  | 120 | 25 | 21% | 40 | - | - | - | - | - | - | - | - | - | 25/120 |
| out_desktop_bench_b3/desktop_bench | desktop |  |  | 30 | 4 | 13% | 0 | - | - | - | - | - | - | - | - | - | 4/30 |
| out_exp_h2 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_rollout_v21 | web |  | /kaggle/input/datasets/khoadangnguye/ornith-gui-lora-v21 | 0 | 0 | 34.7% | 0 | - | - | - | - | - | - | - | - | - | - |
| out_sft_v21 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_sft_v22 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_sft_v24 | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_u_fix | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |
| out_u_fix | web |  |  | 0 | 0 | - | 0 | - | - | - | - | - | - | - | - | - | - |

## 2. Coverage W2 (task tag -> task thuc te trong ket qua)

| # | nang luc | task tag W2 | task tim thay (file/web+desktop) |
|---|---|---|---|
| 1 | Doc truoc khi hanh dong | T21_hiddenval, T25_compute | T21_hiddenval, T25_compute |
| 2 | Nhieu buoc (>=8 hanh dong) | T23_undoredo, T22_order, T13_wizard, T19_wizardsum | T13_wizard, T19_wizardsum, T23_undoredo |
| 3 | Pha vong lap (loop-recovery) | (loai file) | **CHUA CO TASK** |
| 4 | Phuc hoi sau loi | T25_recovery, T08_errorfix | T08_errorfix |
| 5 | Clipboard (select-copy-paste) | T26_clipboard, T16_clipboard2 | T16_clipboard2 |
| 6 | Dieu huong bang phim | T22_keynav, T23_keys | T22_keynav |
| 7 | Scroll / doc ngoai viewport | T07_scroll, T23_table_sort | T07_scroll |
| 8 | Distractor | T20_distractor, T26_distractorlist | T20_distractor, T26_distractorlist |
| 9 | 3D grounding (bbox) | (loai file) | 3d |
| 10 | Desktop that (X11) | (loai file) | T20_2048, T21_form, T21_form_desktop, T22_calc, T22_order, T23_keys, T23_table_sort, T24_text_edit, T25_recovery, T26_clipboard |

## 3. Loi ha tang chi tiet (ep manhinh den / infra_errors)

- **desktop_bench**: 40 ep den + 0 infra_errors
  - T22_calc: 20/20 ep den (win 0/20)
  - T24_text_edit: 20/20 ep den (win 0/20)
- **desktop_bench**: 40 ep den + 0 infra_errors
  - T21_form_desktop: 20/20 ep den (win 0/20)
  - T23_table_sort: 20/20 ep den (win 0/20)

## 4. Canh bao W2

- Nang luc 3 (Pha vong lap (loop-recovery)): **0 file result nao cover**
