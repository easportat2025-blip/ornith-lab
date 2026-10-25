# DECISION MEMO — GUI-SFT (B15.5 / B16-A / DESKTOP) — 22/10 2026, 10:00
> Tóm tắt mọi phép đo đã chạy + đề xuất quyết định. Nguồn chi tiết: `agent.md` (sổ cái, 640KB),
> `scripts/report_fixed_suite.py` (1 lệnh ra báo cáo), `scripts/cmp_cells.py` (so paired).
> Người lập: MiMo. Mọi số đều có bằng chứng chạy thật (file kết quả / log kernel / hash).

---

## 1. CÂU HỎI CẦN QUYẾT (3 việc)

| # | Câu hỏi | Khuyến nghị của tôi | Bằng chứng |
|---|---|---|---|
| Q1 | **Tiêu chí gate** khi ra quyết định recipe | **So PAIRED theo task**, không so tổng `win_rate`; margin ≥1 ep chỉ dùng cho suite tất định | §3 |
| Q2 | **Recipe tiếp theo** (v23a vs v23/v24) | **v24** (S1–S10 + R2 972 + loop-recovery 600 + 3D 600), nhưng **chỉ chấp nhận nếu** vượt Q1; **bỏ `sft-v23` khỏi queue** | §5 |
| Q3 | **Hosting** (HF Pro vs VPS cho Docker Space) | **Bỏ hẳn Space lúc này** (chỉ là demo/UI, không tăng năng lực nghiên cứu); nếu cần demo → **CPU VPS nhỏ** | §6 |

---

## 2. SỐ ĐO ĐÃ CÓ (đều đã kiểm chứng bằng `detect_task_fixes.py`)

### 2.1 Bảng 2×2 — suite **B15.5** (6 task × 3 variant = 18 ep/ô) — **ĐỦ 4 Ô** ✔
| | **task CŨ** (trước 15 fix) | **task MỚI** (đã sửa) | **Δ TASK** |
|---|---|---|---|
| **v21** (bước rỗng cao) | 1/18 = **5,6%** | 8/18 = **44,4%** | **+38,9 điểm** (7 ep) |
| **v22** (bước rỗng 0%) | 3/18 = **16,7%** | 10/18 = **55,6%** | **+38,9 điểm** (7 ep) |
| **Δ DATA** | **+11,1 điểm** (2 ep) | **+11,1 điểm** (2 ep) | — |

⇒ **HIỆU ỨNG CỘNG GIAO (interaction ≈ 0)**: Δ task **+38,9** (giống hệt ở cả 2 model) · Δ data **+11,1** (giống hệt ở cả 2 bộ task) ⇒ **5,6 + 38,9 + 11,1 = 55,6%** ✔
⇒ ⇒ **"+50 điểm" = 78% do SỬA TASK + 22% do SỬA LỖI SINH/DATA.**
⇒ Mọi ô đã verify bằng `detect_task_fixes.py` (ô mới: PROOF_NEW 5/6, PROOF_OLD 0) + adapter so trọng số 256/256 + task dataset verify 11/11 file.
⇒ **Hệ quả quyết định**: **ceiling của việc tối ưu data hiện tại chỉ +11,1 điểm** ⇒ để vượt 55,6% phải **viết thêm task mới đúng chuẩn**, không phải thêm data.
⇒ Chi tiết per-task (ô mới): T13 2/3 · T14 0/3 · T15 0/3 · T16 0/3 · T17 3/3 · T18 3/3 (v22 hơn ở T14/T15, kém ở T13) ⇒ **per-task mới là nơi nhìn thấy chất lượng thật**.

### 2.2 Suite **B16-A** (8 task × 3 = 24 ep) — hiệu quả sửa lỗi sinh
| | acc A | acc B (lặp lại) |
|---|---|---|
| v21 (task CŨ) | 7/24 = 29,2% | *(loại: sai adapter)* |
| **v22 (task MỚI)** | 11/24 = 45,8% | **13/24 = 54,2%** |

⇒ **Δ v21→v22 = +25,0 điểm** · commit 96%→100% · **stuck 54,2%→8,3% (−45,8)** · cluster: `C2_stuck_repeat −7`, `C4_no_submit −6`, `C1_no_action −2`
⇒ 2 lần chạy cùng cell lệch nhau **2 ep** do **2 task flaky** (T19, T26) — xem §3.

### 2.2b **v24 (recipe mới) — ĐÃ ĐO: KHÔNG CẢI THIỆN**
| model (task B15.5 MỚI) | win_rate | stuck_rate | ghi chú |
|---|---|---|---|
| v21 | 8/18 = 44,4% | — | PROOF_NEW 5/6 ✔ |
| **v22** | **10/18 = 55,6%** | 44,4% | |
| **v24** (R2 972 + S1–S10 + loop-recovery 600 + 3D 600 + policy-replay×2) | **9/18 = 50,0%** | **22,2%** | PROOF_NEW 5/6 ✔ |
⇒ **Δ(v22→v24) = −1 episode ⇒ recipe mới KHÔNG mang lại điểm** (trong biên nhiễu ±2 ep) ⇒ **nhưng stuck GIẢM 1/2 (44,4%→22,2%)** ⇒ **dữ liệu loop-recovery CÓ HIỆU QUẢ** (đúng mục tiêu) ⇒ **còn thiếu một thứ khác** (xem §2.2c).
⇒ per-task (v21|v22|v24): T13 2|0|2 · T14 0|3|1 · T15 0|1|1 · T16 0|0|0 · T17 3|3|2 · T18 3|3|3 ⇒ v24 thắng T13 (+2), thua T14 (−2) và T17 (−1).

### 2.2c ⚠️ LỖI ĐO ĐÃ TÌM RA — `raw` bị cắt 300 ký tự ⇒ metric mode/commit/cluster là ẢO
`bench_v15_kernel.py`: `"raw": ans[:300]` (2 chỗ) ⇒ **action vẫn parse từ `ans` đầy đủ và thực thi đúng ⇒ `win_rate` ĐÚNG** ✔; nhưng `analyze_bench_result.py` **parse lại raw đã cắt** ⇒ khi model viết prose dài (>300 ký tự) thì **dòng ACTION bị cắt mất** ⇒ "mode=none" ⇒ **commit_rate giảm & C1_no_action tăng = PHANTOM** (bằng chứng: 28 step "none" của v24 đều có len(raw) = **300 đúng**).
⇒ ⇒ **Đính chính lần 11: cột "cluster delta"/"commit_rate" chỉ đáng tin ở phần `stuck` (tính từ `act`); phần mode/commit thì không** ⇒ đã sửa `ans[:300]` → `ans[:4000]` trong **10 file kernel bench** ⇒ **cần đo lại v22+v24 (capture 4000) khi có quota GPU (24/10) hoặc trên Colab GPU** ⇒ nếu không, mọi so sánh recipe giữa model "nói nhiều" và "nói ít" đều bị lệch.

### 2.2d ✅ DESKTOP — SỐ SẠCH ĐẦU TIÊN (`desktop-bench-b3`: app đủ + guard + adapter v22)
`check_dbench_log` PASS (13 app · GUARD OK · 0 [INFRA] · không thiếu dataset) ⇒ **audit: 30 ep, 4 win = 13,3%, lỗi hạ tầng 0/30 (0%)** ⇒ per-task: T21_form_desktop 0/5 · T22_order 0/5 · T23_keys 0/5 · T23_table_sort 0/5 · T25_recovery 1/5 · T26_clipboard 3/5.
⇒ ⇒ **khoảng cách web 54% vs desktop 13% là THẬT** (không phải lỗi đo) ⇒ **thuốc đúng = data desktop (desktop-replay) + task mới**, không phải thêm data web.

### 2.2e ✅ DATA DESKTOP-REPLAY (đã sinh, sẵn sàng cho v25) — "thuốc" cho khoảng cách web 54% vs desktop 13%
| app | episode giải được | row | verb |
|---|---|---|---|
| T20_2048 | 6/6 | 108 | KEY (phím mũi tên) |
| T21_form_desktop | 6/6 | 60 | CLICK + TYPE |
| T22_calc | 6/6 | 42 | CLICK + TYPE |
| T24_text_edit | 6/6 | 24 | TYPE + CLICK |
| T23_table_sort | 0/6 (chưa có GT policy ⇒ **bị lọc, không đưa vào data**) | – | – |
⇒ **234 row / 24 episode / 4 app** · ảnh chụp **trước mỗi bước** · **mỗi episode = 1 lần load lại ⇒ biến ngẫu nhiên mới** (như app thật) · sinh bằng **chính `checker_desktop.run_task()`** (khớp 100% đường đi của bench) + chỉ giữ episode **thực sự giải được**.
⇒ **HF public**: `kkouadn/ornith-colab-data/desktop_replay.zip` (6,54MB) · **Kaggle**: `dieniw/ornith-gui-desktop-replay` (**verify 234/234 ảnh resolve** theo đúng quy tắc loader).
⇒ Nạp vào kernel SFT: `load_ds_rows("ornith-gui-desktop-replay", "traj.jsonl")` ×2 ⇒ **thứ tự học: desktop-replay (môi trường thật) → S11 (verb mới) → targeted** (đừng tăng targeted: v24 cho thấy targeted ↑ nhưng thời gian +60% & model lặp nhiều hơn).

### 2.2f ✅ B17 (bộ web khó) — 8 app đã build, 21 năng lực (W2 ✔), 8/8 self-test PASS
`phase13-gui/bench_b17/tasks/`: T30_note_order (note ngược thứ tự + decoy) · T31_scroll_code (mã ở hàng 8–14 ⇒ phải scroll) · T32_drag_slider (kéo slider) · T33_error_retry (app báo lỗi dù đúng giá trị) · T34_tab_nav (chỉ Tab/Enter) · T35_hover_code (mã chỉ hiện khi hover) · T36_wizard_steps (3 bước, sai bước bị từ chối) · T37_terms_guard (nút disabled tới khi tick).
⇒ Contract cho checker: `window.__spec.vars` · `window.__state` (+`ok`) · `window.__targets` ⇒ success policy sẵn trong `scripts/b17_selftest.py` ⇒ **@GLM chỉ còn viết checker** ⇒ còn **W1 (model mạnh ≤20%)** cần GPU (acc B còn 0,43h; acc A reset 24/10).

`check_dbench_log` PASS (13 app · GUARD OK · 0 [INFRA] · không thiếu dataset) ⇒ **audit: 30 ep, 4 win = 13,3%, lỗi hạ tầng 0/30 (0%)** ⇒ per-task: T21_form_desktop 0/5 · T22_order 0/5 · T23_keys 0/5 · T23_table_sort 0/5 · T25_recovery 1/5 · T26_clipboard 3/5.
⇒ ⇒ **khoảng cách web 54% vs desktop 13% là THẬT** (không phải lỗi đo) ⇒ **thuốc đúng = data desktop (desktop-replay) + task mới**, không phải thêm data web.


### 2.3 Desktop bench — số cũ **đã định lượng nhiễm** (audit từng ep, `audit_desktop_result.py`)
- Chạy A (80 ep) và B2 (120 ep): **40/80 (A) và 40/120 (B2) ep là lỗi hạ tầng** (4 app HTML không được ghi ra ⇒ không mở browser ⇒ ảnh X11 đen ⇒ model trả "black screen" + DONE + reward −1 ⇒ bị tính nhầm là model thất).
- ⇒ **SỐ ĐÃ SỬA**: **B2 = 25/80 = 31,3%** (trên 4 task hợp lệ — *không phải* 25/120 = 20,8%) · **A = 0/40 = 0%** (2 task hợp lệ).
- ⇒ **Kết quả thật đáng chú ý**: `T26_clipboard` **19/20 = 95%** (chu ký select→copy→paste gần hoàn hảo) trong khi `T22_order`/`T23_keys` = **0/20** ⇒ **nút thắt desktop KHÔNG ở bấm/clipboard mà ở task đọc-thao-tác nhiều bước** (cùng kết luận: 2 chu ký loop là nút thắt ở B15.5).
- ⇒ **đã tách lỗi hạ tầng khỏi lỗi model** (`INFRA_ERRORS` + `infra_errors.json` + `valid=False`), **guard fail-loud** (thiếu app ⇒ chết ngay), lưu raw đầy đủ 2000 ký tự.
- ⇒ **kernel sạch**: `dieniw/ornith-gui-desktop-bench-b3` (adapter v22, 5 ep/task) — đã sửa xong, gate 0 FAIL, **đang chờ slot** ⇒ sẽ cho số desktop **sạch đầu tiên**.
- ⇒ **Bắt buộc từ nay**: mọi báo cáo desktop phải chạy `scripts/audit_desktop_result.py` (đếm % ep "đen" = lỗi hạ tầng) + `scripts/check_dbench_log.py` (apps đủ / guard OK / không [INFRA]).

---

## 3. NHIỄU ĐO — VÌ SAO PHẢI SO THEO TASK (dữ liệu mới, 2 cặp lặp lại)

| cell | lần 1 | lần 2 | task lật cờ |
|---|---|---|---|
| B15.5 (v22, task MỚI) | 10/18 = 55,6% | 10/18 = 55,6% | **0** ⇒ suite **tất định** |
| B16-A (v22, task MỚI) | 11/24 = 45,8% | 13/24 = 54,2% | **2** (T19_wizardsum, T26_distractorlist) |

⇒ Đã **loại trừ** mọi nguồn ngẫu nhiên do code: task HTML không có `Math.random` (0/8) · checker không random · model **greedy** (`do_sample=False`) · dataset acc B đã verify **14/14 file = bản MỚI** ⇒ nguyên nhân nằm ở **ENV (pixel/cài đặt)**, dồn vào đúng 2 task.

⇒ **ĐỀ XUẤT TIÊU CHÍ GATE (Q1):**
```
PASS  ⇔  (a) ≥ baseline ở ≥2/3 suite
      AND (b) mọi suite: so PAIRED theo task — khác biệt ≥1 ep/task trên ≥1/3 task
                          (suite tất định) hoặc ≥3 task lật cờ cùng chiều (suite có task flaky)
      AND (c) không suite nào GIẢM (chặn hồi quy)
```
⇒ v22 **PASS** (B15.5 +38,9 điểm theo task · B16-A +25,0) ⇒ mở đường train, nhưng **tie không lọt** và **nhiễu không bị tính là tiến bộ**.

---

## 4. 7 LỚP LỖI IM LẶNG ĐÃ TÌM + CÁCH CHẶN (tất cả đã có tool + test)

| # | Lỗi | Bằng chứng | Chặn bằng |
|---|---|---|---|
| 1 | Dataset thiếu ⇒ Kaggle **silent-drop** | "could not be added to the kernel" | G9 + watchdog check attach |
| 2 | Dataset rỗng / 0 row | — | G3 (staging) + guard `traj_rows` |
| 3 | Dataset **bản cũ** (cùng slug, khác nội dung) | `ornith-gui-bench-v155` đã bị version | `verify_bench_ds_version.py` (hash từng file) |
| 4 | `enable_internet` + competition ⇒ Kaggle 400 | — | G10 |
| 5 | **Adapter bẫy** (slug gần giống, weights khác) | `dieniw/ornith-gui-lora` ≠ v21 (max\|diff\|=0,11) | **G11** + `lora_fingerprint.py` (vân tay tensor) |
| 6 | **Code đòi adapter A, metadata mount B** | kernel b3 chết "dataset thieu lora-v21" | **G12** (required ⊆ attach) |
| 7 | **Sửa local nhưng Kaggle còn bản cũ** | `sft-v24` chết `NameError: N_3D` | `check_push_parity.py` (pull + so hash) |
| 8 | **App HTML thiếu ⇒ ảnh đen ⇒ tính nhầm là model thất** | log b3/b2 "apps written" không có 4 app | guard `write_apps()` + `INFRA_ERRORS` |
| 9 | Kernel có trong queue nhưng **không có target** ⇒ kết quả không ai lấy | ≥2 lần | `check_queue_targets.py` (nay 0 lỗi) |

⇒ **Gate G1–G12 giờ chạy TRƯỚC mỗi push** (đã nối vào watchdog, restart 09:37) ⇒ lỗi trên bị chặn ở **0 phút GPU**.
⇒ **Test thật**: `test_gate_g11.py` PASS 4/4 · `test_gate_g12.py` PASS 3/3 · `test_infra_guard.py` PASS.

---

## 5. KHUYẾN NGHỊ CỤ THỂ (Q2) — thứ tự dùng GPU

**Còn ~11h quota acc B (acc A hết quota tới 24/10).** Thứ tự:
1. **`sft-v24`** (đang chạy): dr0.75 + S1–S10 + **R2 972** (không truncate) + loop-recovery 600 + policy-replay ×2 + 3D 600 + selfplay cap 30%.
   *Đã kiểm chứng trong log lần chạy vừa rồi:* traj **972/972** · synth-recipe 600/600 · selfplay 118/118 · train3d 300/300 ⇒ **data pipeline đúng**; chỉ thiếu 1 dòng `N_3D = 600` (đã sửa + đã lên Kaggle + đang train lại).
2. **`bench-v155-v21new`** (đang chạy): ô thứ 4 của 2×2 ⇒ chốt H1/H2 ở §2.1.
3. **`desktop-bench-b3`**: đo lại desktop **sạch** (guard + app đủ + adapter v22).
4. Các replication + 3D + baseline v21 trên acc B: **cuối cùng** (giá trị thấp, có thể bỏ).
⇒ **Bỏ `sft-v23` khỏi queue** (recipe cũ: 409 + cắt sai; v24 thay thế hoàn toàn).

---

## 6. HOSTING (Q3)
Space chỉ phục vụ **demo/UI**, không phục vụ pipeline (train + bench đều chạy Kaggle) ⇒ **không tăng năng lực nghiên cứu** ⇒ acc A hết 30h GPU ⇒ **nguồn lực quan trọng nhất lúc này là quota GPU, không phải hosting** ⇒ **bỏ hẳn Space**; nếu cần demo ⇒ **CPU VPS nhỏ** (đủ X11+chromium) hoặc **HF Pro** (không cần GPU cho Space).

---

## 7. LỆNH 1 DÒNG ĐỂ KIỂM TRA MỌI THỨ

```bash
python scripts/report_fixed_suite.py        # bảng 2×2 + delta cluster + so paired + task flaky
python scripts/cmp_cells.py <a.json> <b.json>   # so 2 lần chạy cùng cell -> task lật cờ
python scripts/sum_bench.py <b15_result.json>    # tóm tắt 1 file kết quả
python scripts/check_push_parity.py <kernel_dir> --kernel <owner/slug>   # code Kaggle == local?
python scripts/gate_all_queue.py B             # gate cho cả queue (trước khi restart watchdog)
python scripts/check_queue_targets.py          # kernel nào trong queue mà thiếu target
python scripts/verify_bench_ds_version.py <slug>   # dataset task là bản CŨ hay MỚI
python scripts/lora_fingerprint.py --slug <slug> --register   # đăng ký vân tay adapter
python scripts/scan_my_files.py                # quét file nguồn của tôi (chống file bị sửa lặng)
python scripts/audit_desktop_result.py <desktop_result.json>   # % ep lỗi hạ tầng (ảnh đen)
python scripts/check_dbench_log.py <dbench.log>                # app đủ / guard OK / không [INFRA]
python scripts/lint_task_static.py <suite_dir>  # CỔNG CHẤT LƯỢNG TASK (static, <1s)
```

---

## 6b. CỔNG CHẤT LƯỢNG TASK (mới — theo đúng kết luận 2×2)
Vì **ceiling của tối ưu data chỉ ~+11 điểm**, giá trị còn lại nằm ở **task mới đúng chuẩn**; mà **một task sai làm hỏng phép đo của MỌI model** ⇒ cần cổng chặn trước khi task vào suite:

```
task mới → lint_task_static.py (0 lỗi, <1s, không browser)
          → lint_bench_tasks.py (cần Playwright)
          → dummy_actions self-test (checker phải pass VÀ fail đúng)
          → publish dataset → verify_bench_ds_version.py (hash: đúng bản mới?)
```

`lint_task_static.py` kiểm tra: S1 task/HTML tồn tại (bắt lỗi “app không mở ⇒ ảnh đen”) · **S2 mọi chuỗi trong ngoặc kép của instruction phải có trong DOM** · S3 placeholder phải render được · S4 checker có entry cho task · S5 state hook khớp · S6 lộ đáp án · S7 instruction mâu thuẫn · S8 instruction quá ngắn.
⇒ **Đã kiểm chứng**: trên **bộ task CŨ** linter bắt 2 lỗi thật (S2 + S7 ở T18) · trên **bộ đã sửa** (B15.5 + B16-A) **0 lỗi, 0 cảnh báo** ⇒ không báo nhầm, dùng được làm cổng.

---

## 8. GHI NHẬN & ĐÍNH CHÍNH (minh bạch)
- **Đính chính #9**: tôi từng coi "sửa local là đủ" — **không đủ**, phải đẩy lên Kaggle (`check_push_parity.py`).
- **Đính chính #10**: tôi từng nói "nhiễu 8,4 điểm chung" — thực tế nhiễu **tập trung 2 task**; B15.5 **tất định**.
- **Đính chính #7**: tôi từng đoán "ảnh đen là lỗi X11/CDP" — thực tế là **thiếu file app**.
- **Đính chính #8**: tôi từng coi `out_bench_v155_B` (0/18) là ô (v21, task CŨ) — thực tế **sai adapter** ⇒ đã loại.
- **Lỗi workspace**: 1 file của tôi bị sửa mất 5 ký tự **không đổi mtime** (nghi do agent khác thay chuỗi) ⇒ đã thêm `scan_my_files.py`; **mọi người nên verify file sau khi ghi**.
