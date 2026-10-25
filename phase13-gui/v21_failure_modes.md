# v21 Failure Modes — Phân tích v18 trên B15 (TASK-17)

> **Input:** `phase13-gui/out_bench_v15/b15_result.json` (v18 adapter, 12 task × 3 variant = 36 episode, parse_rate 0.836, win_rate 27.8%).
> **Phương pháp:** đọc `trace` từng bước (raw model output + action + mode + success), `state.tests` (checker từng điều kiện), `reason` (danh sách check fail). Không sửa file nguồn.
> **Mục tiêu (MAIN_QUEST Day 2):** gom cụm lỗi → đề xuất 5-8 task synth targeted để đánh các cụm xuất hiện nhiều nhất. Không tăng steps, không tăng data bừa.

## 1. Tổng quan

| Chỉ số | Giá trị |
|---|---|
| Episode | 36 (12 task × 3 variant) |
| Win | 10 (27.8%) |
| Fail | 26 |
| Task win 3/3 | T03_delayed, T10_canvas |
| Task win 2/3 | T09_coupon |
| Task win 1/3 | T04_slider, T11_counter |
| Task win 0/3 | T01, T02, T05, T06, T07, T08, T12 (7 task) |
| Mode tổng | action 206, legacy 3, none 41 (83.6% parse) |
| Steps tổng | 250 (avg 6.9/episode) |

**Nhận xét chung:** v18 (recipe action-only, 1 dòng ACTION) parse tốt (83.6%) nhưng **fail ở các bước cuối / navigation / đọc text**. Failure mode chính là **prose-before-action** (model viết giải thích thay vì emit action ngay) và **stuck repeat** (click cùng toạ độ không tiến triển). Đây là đúng failure mode đã thấy ở bench v14 (login_done FAIL ở bước submit).

## 2. Bảng cụm lỗi (cluster)

| # | Cụm lỗi | # episode | Task bị | Nguyên nhân gốc (bằng chứng raw) |
|---|---|---|---|---|
| C1 | **Prose-before-action / no action emitted** | 8 | T01v2, T05v1, T08v1/v2, T11v0/v1, T12v0 (5 ep no_action_last) + T01v0/v1 legacy | Model viết giải thích dài thay vì emit `ACTION:` ngay → `mode=none`, step bị lãng phí. Raw T01v2: "The task requires me to fill in the email, password..." (không có ACTION). |
| C2 | **Stuck repeat (click cùng toạ độ)** | 11 | T04 (2), T05 (2), T06 (3), T07 (1), T08 (1), T11 (2), T12 (1) | Model click cùng coordinate nhiều bước liên tiếp không kiểm tra state đã đổi. Raw T04: "Clicking on the track at the 72% position" lặp 2 bước, value không đổi. |
| C3 | **Không đọc text hiển thị / đọc sai target** | 6 | T02 (3), T11 (2), T12 (2) | Model không trích xuất username/password từ note box, không đọc counter target, không đọc code từ page 1. Raw T02v0: "password field currently..." (không điền đúng 'rose42'); T11: "reach 8" thay vì 5. |
| C4 | **Multi-step navigation không hoàn thành** | 6 | T06 (3), T12 (3) | Model không hoàn thành chuỗi read→navigate→type→submit. Raw T06: lặp "Open the Code tab, read the 4-character code, go back to Home tab..." không thực thi. |
| C5 | **Clipboard không hoàn thành (copy xong không paste)** | 3 | T05 (3) | Model chọn text + ctrl+c lặp, không click target + ctrl+v. Raw T05: "text is already selected... copy it" lặp 2 bước. |
| C6 | **Scroll không hoàn thành (không lộ item cuối)** | 3 | T07 (3) | Model click cùng vị trí, không nhấn End/PageDown để lộ item cuối. Raw T07: "More entries are still loading — keep scrolling" nhưng model click lại vị trí cũ. |
| C7 | **Form validation / nhầm field** | 3 | T01 (3) | Model điền một phần field, click confirm password lặp, không tick terms, không submit. Raw T01: "confirm password field is empty... click on confirm password field" lặp. |
| C8 | **Error-recovery không hoàn thành** | 3 | T08 (3) | Model submit form rỗng để reveal lỗi, sau đó click cùng field lặp, không điền giá trị đúng / không submit lại. Raw T08: "Full name field is empty... click on it" lặp. |
| C9 | **Slider miss (click track không đăng ký)** | 2 | T04 (2) | Model click track tại target% nhưng value không đổi (thumb compensation Chromium), không dùng Arrow±. |
| C10 | **Code mismatch (không đọc code page 1)** | 3 | T12 (3) | Model không đọc code từ page 1, type nothing/wrong, click back-and-forth. Raw T12v2: "I don't have the actual code from page 1, I'll..." |

**Tổng fail episode counted:** C1 8 + C2 11 + C3 6 + C4 6 + C5 3 + C6 3 + C7 3 + C8 3 + C9 2 + C10 3 = 48 (episode có thể thuộc nhiều cụm → tổng > 26). Phân bố theo episode (primary cluster):

| Primary cluster | # episode | Task |
|---|---|---|
| C1 prose/no-action | 5 | T01v2, T05v1, T08v1, T08v2, T11v0, T11v1 (6) |
| C2 stuck repeat | 8 | T04v0/v2, T05v0/v2, T06×3, T07v2, T08v0, T11v0/v1 (11) |
| C3 misread text | 4 | T02×3, T11v0/v1 (overlap) |
| C4 navigation incomplete | 6 | T06×3, T12×3 |
| C5 clipboard incomplete | 3 | T05×3 |
| C6 scroll incomplete | 3 | T07×3 |
| C7 form validation | 3 | T01×3 |
| C8 error-recovery | 3 | T08×3 |
| C9 slider miss | 2 | T04v0/v2 |
| C10 code mismatch | 3 | T12×3 |

## 3. Nguyên nhân gốc (root cause) theo task

| Task | Fail # | Nguyên nhân gốc | Bằng chứng (raw, ≤150 chars) |
|---|---|---|---|
| T01_signup | 3/3 | Điền không đủ field + không tick terms + không submit; 1 episode prose-only | "confirm password field is empty... click on confirm password field" (lặp) |
| T02_login | 3/3 | Không điền đúng username/password từ note box (để trống hoặc sai) | "username field is currently empty, so I need to fill it in first" |
| T04_slider | 2/3 | Click track không đăng ký (thumb compensation), không dùng Arrow± chỉnh | "current position is 56%... clicking on track at 72% position" (lặp) |
| T05_shortcut | 3/3 | Copy xong không paste (ctrl+c lặp, không click target + ctrl+v) | "text is already selected... copy it" (lặp ctrl+c) |
| T06_tabcode | 3/3 | Lặp giải thích, không đọc code, không type, không submit (stuck) | "The task is to open the Code tab, read the 4-character code..." (lặp) |
| T07_scroll | 3/3 | Không scroll đến bottom (không End/PageDown), click cùng vị trí | "More entries are still loading — keep scrolling" nhưng click lại vị trí cũ |
| T08_errorfix | 3/3 | Submit rỗng reveal lỗi OK, nhưng không điền giá trị đúng / không submit lại | "Full name field is empty... click on it" (lặp) |
| T09_coupon | 1/3 | Không confirm order (v1) | (chỉ 1 variant fail, order not confirmed) |
| T11_counter | 2/3 | Đọc sai target (8 thay vì 5), click increment quá nhiều, hoặc prose-only | "reach 8, but the task says to reach 5. Wait, let me re-read..." |
| T12_pagecode | 3/3 | Không đọc code page 1, không type, click back-and-forth | "I don't have the actual code from page 1, I'll..." |

**Kết luận root cause chung:** v18 (recipe action-only) **parse tốt** (83.6%) nhưng **thiếu 3 kỹ năng**:
1. **Đọc text hiển thị** (note box, code tab, counter target, field label) → gán sai giá trị.
2. **Hoàn thành chuỗi nhiều bước** (navigate→read→type→submit, scroll→click, copy→paste) → stuck ở bước giữa.
3. **Emit action ngay** thay vì giải thích → prose-before-action ăn budget.

Đây là đúng failure mode đã thấy ở bench v14 (login_done FAIL ở bước submit — model kể trước làm sau).

## 4. Đề xuất 5-8 task synth targeted

Ưu tiên theo tần suất cụm lỗi (C1/C2/C3 xuất hiện nhiều nhất). Mỗi task synth phải **verify được** (checker đọc DOM, không tin self-report) và **không trùng** task B15/B15.5.

| # | Tên synth (đề xuất) | Tình huống UI | Hành vi đúng mong đợi | Check từ đó | Đánh cụm lỗi |
|---|---|---|---|---|---|
| S1 | `read_note_login` | Trang login có **note box nổi bật** ghi username/password; phải đọc rồi điền đúng | Đọc note → điền đúng user/pass → submit → loggedin=1 | loggedin==1, user==note_user, pass==note_pass | C3 (misread text), C1 (prose) |
| S2 | `code_tab_submit` | Tab Code hiện mã 4 ký tự; Tab Home có input + submit; phải đọc mã → navigate → type → submit | Mở Code tab → đọc mã → về Home → type mã → submit → correct=1 | submitted==code, correct==1 | C4 (navigation), C3 (misread), C10 |
| S3 | `scroll_reveal_click` | List lazy-load; item cuối chỉ hiện sau scroll xuống bottom | Scroll (End/PageDown) đến bottom → đợi load hết → click item cuối | clicked==total-1, clickedcount==total, loaded==total | C6 (scroll), C2 (stuck) |
| S4 | `copy_paste_verify` | Source box (text) + target box + nút Verify; phải copy qua phím tắt | Click source → ctrl+a → ctrl+c → click target → ctrl+v → Verify → match=1 | dst==src, pasted>=1, copied>=1, verified==1 | C5 (clipboard), C2 (stuck) |
| S5 | `fill_all_fields` | Form 4 field (name/email/qty/terms) với validation; phải điền tất cả + tick terms + submit | Điền name, email có @, qty 1-9, tick terms → submit → submittedok=1 | submittedok==1, name≠"", email has @, qty 1-9, terms checked | C7 (form validation), C1 (prose) |
| S6 | `slider_to_target` | Slider với target% rõ ràng; phải kéo đến đúng giá trị | Click track tại target% → Arrow± chỉnh đến exact → value==target | value==target, visible text==target | C9 (slider miss), C2 (stuck) |
| S7 | `counter_to_n` | Counter với target N rõ ràng; phải increment đúng N lần rồi submit | Click +1 đúng N lần → submit → submitted=1, count==N | submitted==1, count==target, visible==target | C3 (misread target), C2 (stuck) |
| S8 | `error_recovery_full` | Form rỗng → submit reveal lỗi → điền đúng tất cả field → submit lại → submittedok=1 | Submit rỗng → reveal errors → điền name/email/qty → submit → submittedok=1 | errorsshown==1, submittedok==1, name≠"", email has @, qty 1-9 | C8 (error-recovery), C1 (prose) |

**Ưu tiên synth (theo tần suất cụm lỗi):**
1. **S1 read_note_login** (C3 + C1) — login_wrong_creds xuất hiện 3/3 episode T02, root cause rõ: model không đọc note box.
2. **S4 copy_paste_verify** (C5) — clipboard fail 3/3 T05, model stuck ở copy.
3. **S3 scroll_reveal_click** (C6) — scroll incomplete 3/3 T07, model không scroll.
4. **S7 counter_to_n** (C3 + C2) — misread target 2/3 T11.
5. **S2 code_tab_submit** (C4 + C3) — navigation incomplete 3/3 T06/T12.
6. **S5 fill_all_fields** (C7) — form validation 3/3 T01.
7. **S8 error_recovery_full** (C8) — error-recovery 3/3 T08.
8. **S6 slider_to_target** (C9) — slider miss 2/3 T04 (tần suất thấp nhất).

**Lưu ý cho v21:** các task synth trên **phải verify được** (checker đọc DOM, không tin self-report) và **không trùng** task B15/B15.5. Nếu rollout curate giữ variant 2 làm held-out (bug B), thì synth targeted nên cover cả 3 variant để v21 học đủ pattern. Task mới phải **khó hơn** mỗi ngày (MAIN_QUEST): nên thêm state trung gian (ví dụ S5 thêm "đếm số field đã điền đúng" trước submit).

## 5. Tóm tắt 5 dòng

1. v18 fail 26/36 (72.2%) trên B15 — 7 task 0/3, 5 task 1/3; chỉ 2 task win 3/3 (T03 delayed, T10 canvas).
2. 3 failure mode chính: **prose-before-action** (8 ep), **stuck repeat cùng toạ độ** (11 ep), **không đọc text hiển thị** (6 ep) — đúng failure mode login_done bench v14.
3. Nguyên nhân gốc: v18 parse tốt (83.6%) nhưng thiếu 3 kỹ năng: đọc text, hoàn thành chuỗi nhiều bước, emit action ngay.
4. Đề xuất 8 task synth targeted (S1-S8) ưu tiên theo tần suất cụm lỗi, verify được, không trùng B15/B15.5.
5. @DeepSeek: file này là input cho v21 data synth targeted; tôi không sửa bench_v15/ hay kernel_v21/. Ready cho packaging B15.5 khi pipeline xong.

## 6. Release

- File: `phase13-gui/v21_failure_modes.md` (MỚI, chỉ VIẾT).
- Không sửa `bench_v15/`, `kernel_v21/`, `rollout_curate.py`.
- TASK-17 = DONE.

RELEASE: phase13-gui/v21_failure_modes.md
DONE TASK-17.