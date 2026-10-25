# TRAINING LOOP — Ornith GUI/computer-use agent

> Mục tiêu không phải "train thêm", mà là **tăng capability đo được** trên benchmark khó hơn,
> với bằng chứng chống regression. Mọi run phải tái lập được từ manifest.

## 1. Model & action space

- Base: **Ornith-1.5-9B** (Qwen3.5-VL), giữ trên Kaggle dataset; không copy vào repo.
- Train: QLoRA 4-bit, adapter riêng; base không đổi.
- Observation: screenshot 1280×720 (desktop) hoặc ảnh task; resize theo recipe.
- Action schema (text):
  - `CLICK x y` — x,y normalized 0..1000
  - `TYPE text`
  - `KEY <combo>` — vd `ctrl+a`, `Return`, `alt+Tab`
  - `SCROLL n` — 1 step = 100px; training dùng `SCROLL 5` = 500px
  - `MOVE x y`
  - `DRAG x1 y1 x2 y2`
- Decode: `max_new_tokens` theo run; W1/B17 dùng 512; baseline cũ 256. Không tăng mù.
- Eval: vLLM nếu có; fallback HF generate. Batch nhỏ trên T4.

## 2. Baseline hiện tại

| Run | Benchmark | Kết quả | Ghi chú |
|---|---|---|---|
| v22 | Desktop real (phase14) | 13.3% | repetition/stuck 76.7% |
| v24 | B15/B15.5/B16 aggregate | 60.3% (47/78) | fingerprint `c7d318...` |
| v25b | B15/B15.5/B16/B17 | chưa có | đang fix kernel |
| B17 W1 | action gap | chưa có | v22 chưa học SCROLL/MOVE/DRAG |

**Không so v25b với v24 nếu khác `max_new_tokens`/4-bit.** Gate phải cùng decode config.

## 3. v25b recipe (đang chạy)

- Data: v24 mix + **desktop-replay 282** + **synth-s11 530** (SCROLL/MOVE/DRAG).
- SYS prompt: thêm SCROLL/MOVE/DRAG; giữ format cũ.
- Mục tiêu: đóng action gap, không làm rơi B15/B15.5/B16.
- Sau train:
  1. publish adapter `dieniw/ornith-gui-lora-v25b`
  2. đăng ký fingerprint
  3. chạy B15, B15.5, B16, B17 (4-bit, cùng config)
  4. so v24; gate.

## 4. Gate

Một model mới chỉ được nhận nếu:

1. **>= baseline trên >=2/3 suite** B15/B15.5/B16.
2. **Margin >= 1 episode** trên ít nhất một suite.
3. **Không suite nào regression** quá 1 episode.
4. B17 W1 difficulty <=20%; nếu baseline v22 >20%, phải hạ độ khó trước.
5. Desktop B18: không giảm success; stuck/repetition giảm; recovery task không tệ hơn.

Nếu fail: giữ v24/v25b cũ, ghi lý do, không deploy.

## 5. Vòng lặp tự cải thiện

```
rollout (B17/B18)
  -> log actions + screenshots + checker
  -> failure taxonomy
  -> chọn failure có tần suất cao & sửa được
  -> sinh task/rollout mới (synth + replay + human/expert)
  -> lọc quality + dedupe + balance
  -> train seed/matrix mới
  -> eval 4-bit
  -> gate
  -> deploy hoặc quay lại
```

### Failure taxonomy

| Nhóm | Ví dụ | Data cần |
|---|---|---|
| Stuck/repetition | lặp CLICK cùng chỗ | negative + recovery trajectories |
| Wrong app/window | click nhầm cửa sổ | window-focus tasks |
| Action format | thiếu SCROLL/MOVE/DRAG | synth-s11 |
| Grounding | click sai tọa độ | bbox/point replay |
| Planning | làm sai thứ tự | multi-step demos |
| Recovery | không đóng dialog/lỗi | recovery tasks |
| Text entry | gõ sai/không commit | form/editor tasks |

Mỗi vòng chỉ thêm **một nhóm chính** để đo được tác động; không trộn quá nhiều thay đổi.

## 6. Matrix & seed (PLAN §X)

- Mỗi tuần một **seed mới** và một **ma trận nhỏ**:
  - A: data mix hiện tại + seed mới
  - B: data mix + 1 nhóm failure mới
  - C: data mix + action augmentation mới
- Không chạy 3 run giống nhau chỉ khác seed rồi chọn max; đó là overfit eval.
- Ghi rõ: seed, data hash, code commit, GPU, thư viện, max_new, 4-bit/bf16.
- Nếu một vùng parameter thắng liên tục, **giảm** số run ở vùng đó, tăng độ khó benchmark.

## 7. Data flywheel

### Nguồn
- `ornith-gui-desktop-replay` (282 rows) — trajectory desktop thật.
- `ornith-gui-synth-s11` (530 rows) — SCROLL/MOVE/DRAG.
- v24 mix: real-ui, traj, synth-recipe, 3D, targeted, selfplay.
- B17/B18 rollouts + expert corrections.

### Chất lượng
- Mỗi row: ảnh tồn tại, action parse được, checker pass, không trùng.
- Loại row có action không thực thi được hoặc screenshot sai.
- Giữ tỉ lệ action: CLICK ~50%, TYPE/KEY ~30%, SCROLL/MOVE/DRAG ~20% (điều chỉnh theo benchmark).
- Không thêm quá 20% data mới trong một run nếu chưa có gate.

### Lưu trữ
- HF dataset repo, mỗi version một revision/tag.
- Manifest: `data_version`, `rows`, `sha256`, `source_runs`, `created`.
- Không commit ảnh/dataset vào GitHub.

## 8. Eval protocol

- Cùng một bộ task/seed cho mọi model so sánh.
- 4-bit cho v25b/v26; nếu so bf16 phải ghi rõ, không trộn.
- `max_new_tokens=512` cho W1/B17; baseline cũ 256 chỉ dùng để tham khảo.
- Chạy tối thiểu 2 lần nếu variance cao; báo mean + từng episode.
- Lưu `actions.jsonl`, `reward.json`, `summary.json`, screenshot cho episode fail.
- Không báo "pass" nếu checker không chạy hoặc task `score=-1`.

## 9. Compute plan

| Việc | Nơi | Ghi chú |
|---|---|---|
| Train 9B QLoRA | Kaggle B | 30h/tuần; 1 kernel/lần |
| Eval 4 suite | Kaggle A/C | có thể song song 2 suite/acc |
| Ablation 4-bit | Colab T4 | 25h/ngày; không thay thế gate |
| Data gen/replay | Colab CPU/GPU | chạy khi không train |
| Desktop B18 | Colab/Kaggle CPU | Xvfb + apps; không cần GPU |
| Orchestration | local | OpenChat, heartbeat, registry |

## 10. Run manifest (bắt buộc)

```json
{
  "run_id": "v26-s1",
  "model": "ornith-1.5-9b",
  "base_revision": "...",
  "adapter": "dieniw/ornith-gui-lora-v26-s1",
  "seed": 26,
  "data": {"name": "v26-mix", "rows": 0, "sha256": "..."},
  "code_commit": "...",
  "gpu": "T4|RTX",
  "quant": "4bit",
  "max_new_tokens": 512,
  "train": {"steps": 0, "lr": 0, "batch": 0},
  "eval": {"B15": null, "B15.5": null, "B16": null, "B17": null, "B18": null},
  "gate": "pass|fail|pending",
  "notes": ""
}
```

## 11. Việc tiếp theo

1. v25b kernel chạy → adapter + fingerprint.
2. Chạy 4 gate; ghi manifest.
3. B17 W1 baseline v22; nếu >20% difficulty, hạ.
4. B18 dummy 12/12 → baseline v25b.
5. Mine failure → v26 data; seed 26; matrix A/B/C.
6. Chỉ deploy nếu gate pass; nếu fail, viết post-mortem vào `experiments/`.

---

*Nguyên tắc: capability > loss; gate > cảm giác; tái lập > tốc độ.*
