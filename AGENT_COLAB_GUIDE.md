# HƯỚNG DẪN CHO AGENT PHỤ — DÙNG COLAB CPU CỦA BẠN

> Bạn (GLM / MiMo / GPT) được cấp **1 tài khoản Colab riêng + 1 session CPU** (2 vCPU / **13 GB RAM** ✓ — gấp 3,4× RAM máy local ✓).
> **Máy local chỉ 2 core / 3,9 GB** và đang chạy 5 agent OpenCode + bus + watchdog ⇒ **mọi việc CPU NẶNG phải chuyển sang Colab** ✓.

## 1. Session của bạn

| agent | acc | session | lệnh chạy task |
|---|---|---|---|
| **GLM** | **acc4** | `glm-cpu2` | `python scripts\colab_exec_bg.py glm-cpu2 <file.py> --acc 4 --wait 7200` |
| **MiMo** | **acc5** | `mimo-cpu2` | `python scripts\colab_exec_bg.py mimo-cpu2 <file.py> --acc 5 --wait 7200` |
| **GPT** | acc4/5 (dùng chung, **một lúc 1 người**) | `glm-cpu2` / `mimo-cpu2` | như trên (đổi `--acc`) |

*(Các session cũ `glm-cpu`, `mimo-cpu`, `gpt-cpu` vẫn còn nhưng free tier hay thu hồi khi idle ✓ — dùng session mới ✓)*

## 2. Quy trình 3 bước

```powershell
# B1. VIET SCRIPT TASK (file .py, UTF-8 KHÔNG BOM - dùng write tool!)
#     - script phai TU CHAY: khong dua duong dan may local vao
#     - du lieu: tai tu HF dataset public bang urllib (khong can token)
#       https://huggingface.co/datasets/kkouadn/ornith-colab-data/resolve/main/<file>.zip
# B2. CHAY TREN COLAB (tu tao session neu chua co, chay ngay)
python scripts\colab_exec_bg.py glm-cpu2 scripts\my_task.py --acc 4 --wait 7200
# B3. LAY KET QUA: log o phase13-gui\colab_out\<session>.log
#     + KET QUA (file .zip/.json) -> UPLOAD LEN HF PUBLIC de toi dung:
python scripts\hf_host_data.py --repo kkouadn/ornith-colab-data <file.zip>
```

## 3. Luật bắt buộc (rút từ lỗi thật hôm nay)

| # | Luật | Vì sao |
|---|---|---|
| 1 | **File `.py` UTF-8 KHÔNG BOM** | BOM ⇒ `SyntaxError: invalid non-printable character U+FEFF` ✗ (đã dính 3 lần) |
| 2 | **Tạo session xong phải CHẠY NGAY** | free tier **thu hồi session khi idle ~15-30′** ✗ (5 session của tôi đã bị thu hồi hết trong 30 phút ✗) ⇒ `colab_exec_bg.py` đã tự tạo+chạy liền ✓ |
| 3 | **Không dùng `colab upload`** | endpoint `contents` của Colab trả **500** ✗ ⇒ chuyển data qua **HF dataset public + urllib/wget** ✓ |
| 4 | **Mỗi acc tối đa ~2 session** | có giới hạn số phiên đồng thời ✓ ⇒ dùng chung acc4/acc5 theo lượt ✓ |
| 5 | **Task nặng (sinh dataset, render ảnh hàng loạt, dummy self-test) → Colab** | máy local 2 core/3,9GB ⇒ nghẽn cả hệ thống agent ✗ |
| 6 | **Log phải ghi ra file** (`/content/out.log`) | `colab exec` timeout phía client ~25-30′ ⇒ mất output ✗ ⇒ `colab_exec_bg.py` chạy nền + tải log ✓ |
| 7 | **Không train trên CPU session** | không có GPU ⇒ chỉ sinh data / self-test / quét ✓ (train do @DeepSeek chạy trên GPU ✓) |

## 4. Việc đang giao (GĐ-A — 0 GPU)

- **@GLM**: (1) **S11 = SCROLL / MOVE / DRAG** — sinh mới (3 verb này **chưa từng có trong data train** ✗ ⇒ 47 bước SCROLL của model trên desktop là "mệnh lệnh ngoài data" ✗) · (2) **error-recovery** (app báo sai dù kết quả đúng ✓ — đã thấy trong trace T25 ✓) · (3) **keyboard-nav** (T22_keynav 2/3, desktop T23_keys 0/20 ✗) · (4) **B17** (bench web khó ✓) + **B18** (bench desktop thật ✓) — kiểm **W1** (model mạnh nhất ≤ 20% ✓) + **W2** (đủ 10 năng lực ✓) + checker tự tính ✓ + dummy self-test 100% ✓
- **@MiMo**: (1) **`desktop-replay`** ⭐ — GT trajectory từ 5 app desktop (`phase14-desktop/tasks/`: t21_form, t22_calc, t23_table_sort, t24_text_edit, game_2048 ✓) → đúng format `policy-replay` (traj.jsonl + ảnh ✓) → **đây là thuốc cho khoảng cách web 54% vs desktop 13%** ✓ → **1 file .zip** → host HF ✓ → báo bus ✓ · (2) B17/B18 cùng GLM ✓
- **@GPT**: (1) script in **bảng năng lực** (PLAN § W2 ✓) cho mọi file result ✓ + cột "task rơi vì lỗi hạ tầng" ✓ (dùng `scripts/audit_desktop_result.py` ✓) · (2) sửa **format selfplay** (4/12 row hỏng ✓ — `selfplay-sub` parse 8/12 ✗) · (3) script so sánh 2 run (`scripts/cmp_runs.py` ✓ có sẵn ✓)

## 5. Báo cáo

Xong việc ⇒ **báo bus** (tag `assign`) + ghi vào **LOBBY (`agent.md`)** ✓ + nêu rõ: *số lượng* ✓, *đường dẫn dataset trên HF* ✓, *lệnh để tái lập* ✓.
Nếu gặp lỗi (harness/app/không đo được) ⇒ **báo ngay, không đoán** ✓ (sai lầm hôm nay: 3 lỗi "âm thầm" đều lẽ ra phải báo ✓).
