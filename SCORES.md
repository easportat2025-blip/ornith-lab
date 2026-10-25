# BẢNG ĐIỂM — Bench 60 task (SCORING.md, greedy/batch-8)

> fair = strip fence + base-chat + greedy. Sampling cũ (temp 0.3) chỉ tham khảo.

| Run | Config | game /100 | unity /100 | bpy /100 | **Tổng /300** | Ghi chú |
|---|---|---|---|---|---|---|
| v14 sampling | base | 0 | 0 | 0 | **0** | unfair: prompt thô, chưa strip |
| v14 sampling | r1 | 8 | 53 | 0 | **61** | fence 60/60 |
| v14 sampling | r2 | 14 | 42 | 4 | **60** | fence 55/60 |
| v25 greedy | base-chat | 13 | 50 | 27 | **90** | |
| v25 greedy | r2 | 36 | 37 | 23 | **96** | |
| v25 greedy | r3 | 18 | 43 | 0 | **61** | |
| v28 greedy-batch | base-chat | 20 | 48 | 29 | **97** | |
| v28 greedy-batch | r2 | 32 | 42 | 23 | **97** | |
| v28 greedy-batch | r3 | 21 | 56 | 0 | **77** | |
| v28 greedy-batch | r4 | 32 | 57 | 47 | **136** | merge r3 + data r3/r4, best |
| v30 greedy-batch | base-chat | 19 | 48 | 26 | **93** | |
| v30 greedy-batch | soup(main+aux) | 20 | 0 | 44 | **64** | bpy nhất nhưng unity sập → loại |
| v32 greedy-batch | base-chat | – | – | – | **97** | |
| v32 greedy-batch | r4 | 32 | 57 | 47 | **136** | vẫn vua bench |
| v32 greedy-batch | r6 | 36 | 3 | 4 | **43** | tool-flood làm hỏng format code trực tiếp |
| v31 greedy-batch | base-chat | – | – | – | **97** | deterministic lặp lại |
| v31 greedy-batch | main-ckpt8000 | – | – | – | **31** | OVERFIT: loss 0.2 + epoch 4.1 + bench sập |
| v31 greedy-batch | aux-ckpt7000 | – | – | – | **13** | sai sân (tool-branch chấm bằng game-bench) |
| v31 greedy-batch | soup | – | – | – | **55** | soup từ main-overfit → loại |
| v31 greedy-batch | base/main/aux/soup | – | – | – | **?** | đang chạy |

Kỷ lục: **r4 136/300** (base 97).
O1 (Ornith loop): base 78 (64/14/0/0) vs o1 82 (57/20/5/0) trên thang /400
(game/unity/bpy/pc). O1 hơn base +4 NHƯNG: game rớt 64→57, unity rớt
14→5 (hẹp đi!), chỉ bpy lên 0→20. PC = 0 cả hai (track mới, chưa ai train).
Kết luận: loop hẹp (5 game pygame) làm hẹp model — cần đa dạng + replay.
- Bench v5 (3-way, greedy-batch-8, /400): base 78 (64/14/0/0) vs o1 82 (57/5/20/0) vs **loop1 82 (57/5/20/0)** — loop1 ≡ o1 từng track. Nghi ngờ confound FORMAT (đã đúng).
- Bench v10 RTX bf16 (4-way): base-chat 86 (68/18/0/0) vs o1/loop1/ab1 **126 (54/8/64/0) cả ba y hệt** → bench đo FORMAT prompt (chat vs raw), không đo weights. 3 adapter khác size (465/931/444MB) mà điểm từng task giống nhau = no-op trên bench này. Chờ base-raw (v12) niêm phong.
- CPU-cmp (`adapter-cmp`): 3 adapter cùng 256 keys, weights KHÁC nhau (max diff ~0.03) → greedy plateau thật: SFT đổi weights (học chơi) nhưng argmax trên prompt bench đứng yên. Bench codegen tĩnh chính thức VÔ DỤNG với hướng play/self-play. Eval từ nay = end-to-end build+play (A/B), không chấm code tĩnh nữa.
- Bài học lớn: SFT play/game chỉ đổi hành vi chơi + phân phối code-gần, bench code-spec xa không thấy gì. Eval thật phải là end-to-end build+play (A/B), không phải codegen tĩnh.
