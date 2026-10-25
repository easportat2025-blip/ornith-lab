# HARNESS PLAN — GameCraft self-play loop (Ornith)

> MODEL tự làm TẤT CẢ, đóng 3 VAI MÙ NHAU, wipe context giữa các vai.
> Sửa 11/10: user KHÔNG ra yêu cầu — model tự đề xuất.
> [User có thể bổ sung ràng buộc khung sau, hiện chưa có]

## 1. Vòng lặp 3 vai (per cycle, ~5 game)

```
VAI 1: REQUIREMENTS (đề xuất)
  input: context RỖNG + dòng nhắc "hãy đề xuất 5 game + spec chơi được".
  output: 5 bản spec (luật, thắng/thua, state/action cần có).
      |
  XÓA CONTEXT (vai sau không biết ai đề xuất)
      |
VAI 2: CREATE (xây dựng, từng spec một)
  input: 1 spec + interface bắt buộc (get_state/do_action, headless).
  tools: write_file, run_python verify.
  output: 1 file game chạy được.
      |
  XÓA CONTEXT (vai sau không biết ai tạo)
      |
VAI 3: PLAY + REVIEW (chơi + chấm)
  input: file game (không spec gốc, không tác giả).
  tools: get_state/do_action loop K turns.
  output: điểm 1-5 + bug + verdict (có fix được không).
```

## 2. Vì sao 3 vai mù nhau

- Đề xuất không nịnh: vai 1 không biết mình sẽ phải tạo/chơi.
- Tạo nghiêm túc: vai 2 không biết spec dễ/khó do ai.
- Chấm khách quan: vai 3 không biết game của ai (kể cả của chính nó) —
  đúng kiểu blind review, chống tự khen.

## 3. Học từ đâu ([học từ đó] theo ý user)

- Trajectory full 1 cycle: spec → code → play-log → review.
- Điểm số theo dõi qua cycles: game sau có khá hơn game trước không
  (chỉ số tiến bộ duy nhất cần).
- Data này train run sau: đúng hành vi agent thật (đề xuất + xây + chơi).

## 8. GIAO THỨC A/B (user chốt 11/10, thay 3-vai-mù)

- A = ĐẠO DIỄN (requester + critic): ra yêu cầu, SOI render bằng vision,
  chê cụ thể ("tay hơi to"), playtest, tối đa 5 lượt/yêu cầu,
  NHẬN XÉT KHÓ TÍNH, cấm khen suông.
- B = THỢ XÂY (doer): tạo Blender character → sửa theo chê → export file
  → thêm RIG → tự tạo ANIMATION → build game có nhân vật → TỰ CHẠY.
- Ví dụ 1 round: A "tạo char Anime Blender" → B làm → A "tay hơi to"
  → B sửa → A "ok, từ char này tạo GAME có animation" → B xuất+rig+
  animate+chạy → A chơi thử → verdict.
- A/B có thể là cùng weights khác system prompt, hoặc 2 adapter khác nhau.
- Trajectory A↔B (yêu cầu-chê-sửa-verdict) là data train quý nhất.

## 7. RUNNER v1 (`harness/runner.py`, chạy local với Ollama)

- 5 game/cycle, 3 vai mù nhau (mỗi vai messages mới hoàn toàn).
- Tools: write_file / run_python (headless pygame) / get_state / do_action.
- ĐIỂM DO HARNESS CHẤM (không phải model tự chấm), thang 10/game:
  boot chạy được 2 + API đủ 1 + chơi (sống ≥20 turns 2, có tiến triển điểm 1)
  + review (chỉ ra bug 1, gợi ý sửa 1).
- `leaderboard.json` + `trajectories.json` + `halloffame.json` (top-5 mọi cycle).
- Cách học: lọc trajectory điểm cao → SFT (RFT); sau này GRPO online.

## 6. CHỐNG HACK + TỰ TIẾN HÓA (user chốt 11/10)

- ÉP TRUNG THỰC 3 lớp (prompt một mình không đủ, policy RL lách được):
  1. System prompt: hành động/báo cáo phải trung thực, bịa = lỗi nặng nhất.
  2. Cross-check mù: vai review (không biết tác giả) đối chiếu claim
     với log/render thật — nói sai là trừ điểm.
  3. Bẫy hiệu chuẩn: cài sẵn task bất khả thi — model nào dám nhận
     "làm được" là rớt; nhận "không làm được + lý do" được cộng.
- CHẤM BẰNG MẮT (vision-grounded, cho Blender và game):
  render/chụp màn hình → model mô tả NHÌN THẤY GÌ → đối chiếu prompt:
  thiếu element nào, lệch gì → điểm = đủ trừ lệch. Không chấm code mù.
- ACT cũng ăn điểm: mỗi action hợp lệ +1 phụ, action vô nghĩa/spam -1.
- TỰ TIẾN HÓA đa trục (không chỉ điểm game):
  + Kỹ năng game (điểm review), kỹ năng máy (số steps/token mỗi task
    giảm dần = thưởng hiệu quả), curriculum (mở tool mới khi đủ điểm).
  + Điểm tiến bộ = delta cycle sau - cycle trước, từng trục riêng.

## 4. NÂNG CẤP 11/10: Ornith CÓ vision + hall-of-fame + env

- Vision verify từ config gốc `ornith-ai/Ornith-1.5-9B`: ViT depth 27,
  patch 16, merge 2 + VIDEO (temporal_patch 2) + image/video tokens.
  → Vai PLAY/REVIEW được dùng MẮT (screenshot mỗi N turns kèm state JSON).
  Lưu ý: bản GGUF cần file `mmproj` đi kèm mới có vision (check repo
  `ornith-ai/Ornith-1.5-9B-GGUF` khi pull); không có thì rớt về text-only.
- Môi trường tạo: sandbox LOCAL — harness tự probe (python? pygame?
  blender? node?) rồi gò creation theo cái có. (Cần hỏi user máy cài gì.)
- HALL OF FAME top-5 mọi cycle (`halloffame/` + `leaderboard.json`):
  chỉ giữ 5 game điểm cao nhất, cycle mới phải vượt mới thay, rớt là xóa.

## 9. XOAY ĐỀ + ĐA ENGINE (user chốt 11/10, loop v2 Kaggle)

- BẮT BUỘC mix engine mỗi cycle, không bao giờ lặp y cycle trước.
  Cycle 2: pygame maze + godot pong + unity enemy-AI + bpy oto +
  pygame asteroids (cycle 1 là 5x pygame khác).
- Mức verify TRUNG THỰC theo engine (không nổ):
  pygame = full play-loop; godot = boot parse headless (fallback static);
  unity = static (MonoBehaviour+Start/Update+API, không có engine);
  bpy = render Blender thật.
- STATIC_ROWS (gd/cs/bpy verified) trộn vào train mỗi phase cùng play data.
