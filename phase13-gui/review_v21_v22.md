# Review code pipeline v21 / v22 / curate (TASK-21, GLM) — 19/10

**Phạm vi (CHỈ ĐỌC, KHÔNG sửa file nguồn):**
`kernel_v21/gui_sft_v21.py`, `kernel_v22/gui_sft_v22.py` (+ `kernel_v22_B/` **giống hệt** v22 — 0 dòng khác biệt),
`kernel_v20/gui_sft_v20.py`, `rollout_curate.py` (+ `test_curate.py`),
`kernel_rollout_base/`, `kernel_rollout_v20/`, `kernel_rollout_v21/rollout_kernel.py`,
tham chiếu `kernel/gui_sft.py` (v18 — đã chạy thật, n_train 2808 / 500 steps).

**Phương pháp:** `difflib` unified-diff từng fork với v18 + đọc logic từng hunk + `py_compile` cả 7 file +
**chạy thật** `rollout_curate.select()` trên dữ liệu giả để kiểm chứng nghi vấn + đối chiếu schema với
file thật trên đĩa (`selfplay_dataset/traj.jsonl`, `selfplay/gui-selfplay-d2.jsonl`).

**Kết quả tổng:** `py_compile` cả 7 file **OK** (không lỗi cú pháp). Diff v21 so với v18 **rất gọn (52 dòng)** — không thấy
biến chưa định nghĩa. Schema row rollout ↔ curate **khớp 100%**. Tìm được **4 lỗi cứng** (1 cái đã chứng minh bằng code)
và **1 sai lệch protocol** (train ≠ serve) cần xử lý trước khi đốt GPU-giờ.

---

## A. LỖI CỨNG (làm hỏng run hoặc làm sai dữ liệu — nên sửa TRƯỚC khi push)

### A1. `load_ds_rows` trùng substring → train3d / train3d-hard đọc nhầm dataset (v22)
- **Dòng:** `kernel_v22/gui_sft_v22.py:462` → `load_ds_rows("gui-train3d", "traj.jsonl")` và `:466` → `load_ds_rows("gui-train3d-hard", "traj.jsonl")`
- **Vì sao hỏng:** hàm match bằng **substring** của đường dẫn (`substr in root`), mà
  `"gui-train3d"` **nằm trong** `"ornith-gui-train3d-hard"`. `os.walk` trả thư mục theo thứ tự scandir
  (KHÔNG bảo đảm alphabet trên Linux). Nếu dir `-hard` được duyệt trước → **cả 2 lệnh load trả CÙNG dataset `-hard`**:
  `t3d_rows` = hard, `t3dh_rows` = hard (đếm 2 lần), còn train3d thường **không bao giờ được load** → lẫn dữ liệu sai + mất data.
- **Chứng minh:** khớp chuỗi thật (chạy local): `substr='gui-train3d'` match cả
  `/kaggle/input/ornith-gui-train3d` **và** `/kaggle/input/ornith-gui-train3d-hard`.
- **Sửa 1 dòng:** so khớp **basename chính xác** thay vì substring, ví dụ
  `if fname in files and os.path.basename(root) == substr:` (đổi tên gọi dataset cho khớp basename),
  hoặc đổi 2 lệnh call thành `("ornith-gui-train3d")` / `("ornith-gui-train3d-hard")` + so khớp basename.
- **Cùng kiểu:** `"gui-selfplay"` / `"policy-replay-data"` hiện chỉ khớp 1 dir ✔ (chưa lỗi, nhưng nên khoá chặt luôn).

### A2. `rollout_curate.select()` — "bỏ step cuối của episode FAIL" KHÔNG chạy khi step cuối là prose → **huấn luyện nhầm action sai**
- **Dòng:** `rollout_curate.py:126-128` (`if not win and i == len(rs) - 1:`)
- **Vì sao hỏng:** `i` là chỉ số trong `rs` (mọi row), nhưng các row `mode="none"` (prose, không có action) đã bị
  `continue` **trước đó** (dòng 113). Nếu bước cuối của episode fail là **prose** (model hết budget → không kịp emit action,
  đúng case mode=none 41/250 step ≈ 16% theo số liệu của bạn), thì **action sai cuối cùng vẫn được giữ lại huấn luyện** —
  đúng cái lỗi mà docstring nói là phải loại.
- **Chứng minh (chạy thật `select()`):**
  - TH1 (3 action khác nhau + bước cuối prose): `stats = (dup=0, drop_last=0, loop_ep=0, masked=0, repeat=0)`,
    kept = `[CLICK 100 100, CLICK 300 300, **CLICK 500 500**]` → **action sai cuối vẫn còn** ✔ bug.
  - TH2 (bước cuối là action): `drop_last=1` → bị loại đúng ✔ (để so sánh).
- **Sửa 1 dòng:** tính chỉ số của **action cuối cùng** rồi so sánh với `i`:
  ```python
  act_idx = [j for j, rr in enumerate(rs) if (rr.get("action") or "").strip()
             and rr.get("mode") in ("action", "legacy")]
  last_act_i = act_idx[-1] if act_idx else -1
  ...
  if not win and i == last_act_i:      # thay cho i == len(rs) - 1
  ```

### A3. ID dataset self-play không khớp giữa staging và kernel (VERIFY trước khi push)
- **Dòng:** `rollout_curate.py:240-242` ghi `dataset-metadata.json` với `"id": "hhjiji/gui-selfplay"`
  (cả `selfplay_dataset/` và `selfplay_dataset_v20/` đều ghi id này), trong khi
  `kernel_v22/kernel-metadata.json` attach **`"khoadangnguye/gui-selfplay"`**.
- **Vì sao đáng lo:** nếu dataset thật được up dưới slug `hhjiji/gui-selfplay` thì kernel đang attach **dataset khác**
  (hoặc push lỗi "dataset not found"). Mount path vẫn là `/kaggle/input/gui-selfplay` nên **không lộ ra bằng log** —
  chỉ lộ khi số row lệch.
- **Sửa:** xác nhận dataset nào thật sự tồn tại + version nào (`gui-selfplay` v1/v2?), rồi đồng bộ `id` trong
  `dataset-metadata.json` **và** `dataset_sources` của kernel (1 dòng mỗi bên).

### A4. v22 **mất** fallback tìm ảnh mà v21 có (rủi ro mất sạch row, chỉ lộ ở log)
- **Dòng:** `kernel_v22/gui_sft_v22.py:336-347` (`_resolve`) — diff v21→v22 **xoá** 5 dòng fallback
  `for root, _, files in os.walk(base): if name in files: return ...` (v21 có, comment "TASK-21: Kaggle auto-extract zip...").
- **Vì sao đáng lo:** v18/v21 thêm fallback vì **Kaggle auto-extract zip server-side**: ảnh nằm ở
  `<dataset>/<ten-zip>/<path>` và file `.zip` bị strip → không có gì để giải nén → `_resolve` trả None → **row bị drop âm thầm**
  (chỉ thấy ở log dạng `xxx: 0/N rows`).
- **Ảnh hưởng:** dataset **gui-selfplay** hiện an toàn (`shots.zip` → giải ra `<dataset>/shots/<base>.png`, khớp `rel="shots/..."` ✔),
  nhưng 2 dataset **mới** (`train3d`, `policy-replay`) chưa kiểm chứng layout → nếu ảnh nằm trong subdir của zip là mất sạch.
- **Sửa:** copy lại đúng 5 dòng fallback của v21 vào v22 (hoặc tốt hơn: đổi `_resolve` sang duyệt **toàn bộ** `/kaggle/input/<dataset>`).

### A5. **Protocol lệch**: SYS lúc TRAIN ≠ SYS lúc SERVE (v21/v22 vs bench/rollout)
- **Dòng:** `kernel_v22/gui_sft_v22.py:166-171` → SYS = **v18** ("output ONE action line only… No explanation.")
  trong khi `kernel_rollout_v21/rollout_kernel.py:36-45` (và mọi kernel bench v15/v16/v21/v22) dùng SYS **reasoning**
  ("THINK: … / ACTION: … / the LAST line MUST start with 'ACTION:'").
- **Vì sao hỏng:** adapter v22 sẽ được train với prompt A nhưng lúc đo (bench/rollout) lại dùng prompt B →
  lệch phân bố prompt, và mọi self-play row thu được dưới prompt B lại được train với prompt A.
- **Kèm theo:** kernel train **không có** cờ `enable_thinking` (rollout/bench có, `ORNI_THINK=0`) → phía train vẫn bật
  thinking mặc định trong chat template ⇒ **root cause C1 chưa được xử lý ở phía train** (bạn mới tìm ra ở inference).
- **Sửa (1-2 dòng mỗi bên):** chọn 1 SYS duy nhất cho cả train và serve. Nếu giữ reasoning → dùng SYS của v20 trong v22
  + target `THINK:`/`ACTION:` (tức là v22 phải nhánh từ **v20**, không phải từ v21/v18) + thêm `enable_thinking` cùng cờ
  `ORNI_THINK` vào kernel train. Nếu giữ action-only → đổi SYS của bench/rollout về action-only (và nhớ bật `enable_thinking=False`).
- **Ghi chú chiến lược:** `kernel_v22` là fork từ **v21** (action-only) trong khi adapter đang chạy là **v20** (reasoning) →
  v22 (nếu chạy) sẽ **lùi về format action-only**. Parser bench chấp nhận cả 2 ✔ nên không crash, nhưng đo được gì thì phải nói rõ.

---

## B. LỖI MỀM / RỦI RO CHẤT LƯỢNG (không làm hỏng run nhưng nên sửa)

| # | Vị trí | Vấn đề | Sửa 1 dòng |
|---|---|---|---|
| B1 | `gui_sft_v22.py:497-500` | Log dính chuỗi: thiếu dấu cách giữa `train3d {n}` và `(+hard …)`, và lặp `(+hard {len(t3dh_rows)})` **2 lần** → log đọc sai số liệu | thêm `+` giữa 2 f-string, xoá 1 lần lặp |
| B2 | `rollout_curate.py:184-189` | `n_win` đếm **trước** khi cắt `cap` → dòng in "win N" có thể lệch với số row thật | tính `n_win` sau `kept = kept[:a.cap]` |
| B3 | `rollout_curate.py:130-131,185` | Sort "win trước" rồi mới cắt cap → nếu số row win > cap thì **near-miss (fail) rows biến mất hết** | cắt cap theo tỉ lệ win/fail, hoặc cap riêng 2 nhóm |
| B4 | `gui_sft_v22.py:463-466` | `load_ds_rows` **fail-soft**: thiếu dataset chỉ log "khong thay … -> skip", train vẫn chạy → dễ lỡ dataset mà không biết | `assert`/raise cho dataset bắt buộc (selfplay, train3d) hoặc ghi `data_missing` vào `gui_result.json` + post-run check |
| B5 | `gui_sft_v22.py:310-356` | Mọi dataset giải nén vào **cùng** `ext = /kaggle/working/real_imgs`; fallback theo **basename** có thể trả **ảnh của dataset khác** nếu trùng tên file | `ext` riêng cho từng dataset (vd `WORK/ds_<substr>`) |
| B6 | `gui_sft_v22.py:258-263` (`to_msgs`) | `r.get("action")` → None thì `r["point"]` ⇒ **KeyError** nếu row thiếu cả 2 (chưa gặp, nhưng dataset mới chưa xác minh) | `r.get("point")` + fallback `"DONE"` |
| B7 | `gui_sft_v22.py` (eval) | `train-sub` lấy `train_rows[:12]` → **chỉ đo synth** (trùng v18), **không đo** selfplay/targeted/train3d | thêm 1 eval slice cho targeted + selfplay (8-12 row) |
| B8 | `gui_sft_v22.py:14-16` | `N_TARGETED = 250` (board ghi 600 episode) → targeted sinh **~980 row**; `STEPS_V22` auto-scale ⇒ ước tính **674-888 steps** (≈1.35-1.8× v18 500 steps ≈ 1.3-1.8 GPU-giờ) chưa tính phần eval/mini-eval | chốt số steps + ngân sách GPU trước khi push |
| B9 | dữ liệu thật trên đĩa | Self-play hiện chỉ **123 row** (9 task, variant {0,1}) ⇒ **≈3%** data; `cap_sp` (≈1623) không bao giờ kích hoạt | rollout v21 (N_REPS=2 → 72 ep) chạy xong rồi curate lại trước khi push v22 |
| B10 | `gui_sft_v20.py` (`EvalResult`) | `dict` override `__iter__` trả `(acc, leak)` ⇒ `for k in result` trả **tuple** thay vì key (json.dump vẫn OK) | dùng object có thuộc tính, hoặc trả tuple thuần |
| B11 | 3 kernel rollout | `base` vs `v20` vs `v21` **chỉ khác đúng 1 dòng** `N_REPS` (base=2, v20=1, v21=2) ⇒ dễ push nhầm bản | ghi rõ N_REPS vào log đầu kernel + đọc lại trước khi push |
| B12 | `gui_sft_v22.py` (metadata) | `machine_shape: NvidiaRtxPro6000` + `competition_sources` ✔ đúng như kernel exp đã chạy được; `enable_internet: false` ✔ | không cần sửa |

---

## C. ĐÃ KIỂM TRA & ĐÚNG (không cần sửa)

1. **Schema row rollout ↔ curate khớp 100%**: rollout ghi `task_id, variant, rep, step, image("shots/…png"), instruction,
   target, action, mode, prose_lines, extra_actions, n_new, win, n_fail_checks, n_checks, fail_reason` — curate đọc đúng
   các key này (`r["image"]`, `r.get("action")`, `r.get("mode")`, `r.get("win")`, `r.get("n_fail_checks")`, `r.get("target")`) ✔.
2. **Bundle zip**: `rollout_kernel` ghi `rollout_rows.jsonl` + `rollout_summary.json` + ảnh theo đúng rel `shots/xxx.png` ✔
   → `curate` `z.read(rel)` khớp ✔; curate ghi `shots.zip` với ảnh ở **top level** → Kaggle giải ra `<dataset>/shots/<base>.png`
   khớp `rel` trong `traj.jsonl` ✔ (đúng luật "Kaggle CLI không upload file trong subdir").
3. **Held-out variant**: `--exclude-variants 2` chạy đúng — file thật `selfplay_dataset/traj.jsonl` chỉ có variant **{0,1}** ✔.
4. **Công thức cap 30%**: `cap_sp = int(0.30*base_n/0.70)` đúng toán (sp = 30% của tổng) ✔.
5. **Steps auto theo data giữ 2 epoch**: `max_steps = int(STEPS * n_train/2808)` ✔ (đúng công thức của v19).
6. **Diff v21 vs v18 gọn (52 dòng)**: thêm loader self-play + cap + STEPS_V21 + log + result json; **không thấy** biến chưa định nghĩa,
   key trai, thiếu import. (Phần thêm indent lệch trong `gui_result.json` là **hợp lệ** — dict literal, `py_compile` OK.)
7. **`kernel_v22_B/gui_sft_v22.py` giống hệt `kernel_v22`** (0 dòng khác) → dùng 1 trong 2, không cần fork thêm.
8. `py_compile` OK cho cả 7 file: v18, v20, v21, v22, v22_B, rollout_curate, rollout_v21, gen_synth_targeted ✔.
9. `load_ds_rows` vẫn an toàn với dataset đã chạy thật: `gui-traj` ✔, `real-ui` ✔ (v18 train OK).

---

## D. VIỆC CẦN VERIFY (không kiểm chứng được offline)

- **V1** — schema của dataset **`train3d` / `train3d-hard` / `policy-replay-data`**: chưa có trên đĩa, không kiểm được
  `key "action"` / định dạng. Nếu action ghi kiểu `"CLICK (x, y)"` hoặc dict → `to_msgs` sẽ đưa **target sai định dạng**
  (v18 kỳ vọng `CLICK x y` / `TYPE text` / `KEY name` / `DONE`).
- **V2** — dataset `gui-selfplay` thật sự tồn tại ở slug nào, version nào (xem A3).
- **V3** — layout ảnh của dataset mới (ảnh nằm trực tiếp hay trong `<zip>/<path>`) — quyết định có cần A4 hay không.
- **V4** — `n_fail_checks` của checker có phản ánh "gần đúng" không (curate dùng `n_fail_checks <= max_fail` để giữ near-miss).
- **V5** — có muốn giữ `enable_thinking=False` trong **train** không (A5) — ảnh hưởng lớn tới kỳ vọng về C1.

---

## E. ĐỀ XUẤT THỨ TỰ XỬ LÝ (ưu tiên tiết kiệm GPU-giờ)

1. **A5** (SYS train = serve + `enable_thinking`) — quyết protocol 1 lần, áp dụng cho mọi kernel sau này.
2. **A1 + A4** (sửa `load_ds_rows`: so khớp basename + giữ fallback `base`) — 2 chỗ, 10 dòng; bảo đảm data v22 không rơi rác âm thầm.
3. **A2** (curate drop-last) — 3 dòng; sửa ở nguồn để cả dataset d2 lẫy mọi lần curate sau đều đúng.
4. **A3** (id dataset) + **B4** (fail-soft → assert) — để lỗi nổ lên thay vì im.
5. **B8 + B9** (chốt steps + rollout đủ data rồi curate lại) — quyết định khi nào đốt GPU-giờ.

*Review bởi GLM, 19/10 — chỉ đọc, không sửa 1 dòng nào của file nguồn. Mọi ví dụ trong mục A đã chạy thật local.*
