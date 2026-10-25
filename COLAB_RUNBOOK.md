# COLAB CLI — GPU thứ 2 cho pipeline (22/10/2026)

> Lý do: **acc Kaggle A hết quota (0/30h)**, acc B còn ~1,7h ⇒ cần GPU thay thế ✓.
> `google-colab-cli` là **CLI chính thức của Google** (6/2026 ✓) — chạy được **trên Windows** ✓ (dù README ghi "Linux/macOS only" ✓ — đã test thật ✓).

## 1. Trạng thái ĐÃ kiểm chứng (không phải tin đồn)

| mục | kết quả |
|---|---|
| CLI | `google-colab-cli` **0.7.5** ✓ đã cài (nâng từ 0.6.0 ✓) tại `C:\Users\Admin\AppData\Local\Programs\Python\Python312\Scripts\colab.exe` ✓ |
| Chạy trên Windows | ✅ **CÓ** — `colab --help` OK ✓ |
| Đăng nhập | ✅ **ĐÃ ĐĂNG NHẬP** (CLI gọi được backend ✓ — `colab sessions` trả lời ✓) — tài khoản `easportat2025@gmail.com` ✓ |
| Cấp GPU | ✅ `colab new -s orn-probe --gpu T4` → **Session READY** ✓ (T4 16GB ✓, disk 75,5GB ✓, RAM 13,6GB ✓, **2 CPU core** ✗, torch 2.11+cu130 + CUDA sẵn ✓) |
| `colab usage` | balance **0.00 compute units** ✓ (nhưng free tier **vẫn cấp T4** ✓) |
| Drive cache | ❌ cần **user authorize 1 lần** (URL do CLI in ra ✓) ⇒ mới cache được 18GB base + wheels ✓ |

## 2. Lệnh cốt lõi (đã test phần `new`/`exec`/`status`/`sessions` ✓)

```powershell
$colab = "C:\Users\Admin\AppData\Local\Programs\Python\Python312\Scripts\colab.exe"

$colab new -s orn --gpu T4          # cap GPU (free) | --gpu L4 | --gpu A100 (Pro)
$colab status -s orn                 # xem tai nguyen
$colab exec  -s orn -f script.py     # chay file LOCAL tren VM (noi dung duoc gui len)
$colab install -s orn torch transformers unsloth trl peft datasets
$colab upload -s orn LOCAL REMOTE    # gui file
$colab download -s orn REMOTE LOCAL  # tai file ve
$colab log -s orn -o out.md          # xuat log
$colab stop -s orn                   # giai tai nguyen
$colab run --gpu T4 train.py         # EPHEMERAL: cap -> chay -> tu torn (1 lenh)
```

> ⚠️ **Bẫy đã dính:** file gửi lên **KHÔNG ĐƯỢC CÓ BOM** ✗ (PowerShell 5.1 `Out-File -Encoding utf8` **thêm BOM** ✗ ⇒ `SyntaxError: invalid non-printable character U+FEFF` ✗) ⇒ **luôn tạo file .py bằng UTF-8 không BOM** ✓ (dùng `write` tool ✓ hoặc `[IO.File]::WriteAllText($p,$t,(New-Object Text.UTF8Encoding $false))` ✓).

## 3. Plan chạy trên Colab (theo thứ tự lợi ích)

### (a) Ngay hôm nay, 0 đồng — **cache tài nguyên** (sau khi user authorize Drive ✓)
```powershell
$colab new -s orn-stage --gpu T4
$colab drivemount -s orn-stage          # USER: mo URL, cap quyen, Enter
$colab exec -s orn-stage -f scripts/colab_stage.py   # tai base 18GB + wheels vao Drive
```
⇒ cache ở `/content/drive/ornith-cache/{base,wheels,data}` ✓ ⇒ các lần sau **không tải lại 18GB** ✓✓.

### (b) Sẵn sàng để chạy train trên Colab
- **Base model**: `ornith-ai/Ornith-1.5-9B` (public trên HF ✓ — không cần token ✓).
- **Data**: upload 5 file `.zip` từ máy local (tổng ~75MB ✓) ⇒ **không cần Kaggle key trên VM** ✓✓.
- **Output**: `colab download` adapter về máy ⇒ upload lên Kaggle (`dieniw/ornith-gui-lora-v25`) ⇒ **gate trên Kaggle** ✓ (để số liệu so sánh đồng nhất ✓).

### (c) ⚠️ GIỚI HẠN CỨNG của T4 (free) — phải biết trước
| hạng mục | T4 | Hệ quả |
|---|---|---|
| VRAM | 16GB | model 10B **bf16 cần ~20GB** ✗ ⇒ **bắt buộc 4-bit (QLoRA)** ✓ ⇒ số liệu **KHÔNG so sánh được** với run bf16 trên Kaggle ✗ ⇒ chỉ dùng cho **thử nghiệm/so sánh nội bộ** ✓ |
| RAM | 13,6GB | nạp model + data phải tiết chế ✓ |
| CPU | **2 core** | sinh targeted 3681 row (CPU-heavy ✗) sẽ **rất chậm** ✗ ⇒ nên **tạo sẵn data trên Kaggle rồi upload .zip** ✓ |
| Disk | 75GB | đủ base 18GB ✓ + wheels ✓ + data ✓ |

⇒ **Kết luận chiến lược:** T4 free = **"phòng thí nghiệm 4-bit"** ✓ (để phát triển harness + ablation data + smoke test GRPO ✓), **không thay được** backend bf16 ✗.
⇒ **Muốn có GPU thật thứ 2 ⇒ Colab Pro (~$10/tháng ✓) ⇒ A100 40GB / L4 24GB ✓** ⇒ **quyết định này thuộc về user** ✓ (tương tự câu hỏi HF PRO đã bỏ ✓).

## 4. Có thể dùng Colab để làm gì NGAY (0 đồng, không cần Drive)
1. **Smoke-test kernel GRPO-v1** ✓ (chạy 5-10 step trên T4 4-bit để chắc không lỗi API ✓ — tiết kiệm 1 lần 2h GPU trên Kaggle ✓✓).
2. **Sinh sẵn data CPU-heavy** (targeted 3681 row ✗ — chậm trên 2 core ✗ ⇒ không khuyến nghị ✓).
3. **Dev harness bench/desktop** ✓ (không cần GPU ✓).
4. **Chạy bộ bench B17/B18 ở chế độ 4-bit** ✓ ⇒ *dùng để so sánh TƯƠNG ĐỐI* (không so với số bf16 ✓).

## 5. Việc user cần làm
- **(A)** Authorize Drive (URL CLI in ra ✓) ⇒ bật cache 18GB ✓ *(tùy chọn ✓)*.
- **(B)** Quyết định: **mua Colab Pro** (A100/L4 ⇒ GPU thật thứ 2 ✓ ~$10/tháng ✓) **hay** chỉ dùng T4 free làm lab 4-bit ✓.
- **(C)** Cân nhắc: **cùng thứ đó còn cần VPS** cho bản web "sống" (đã bỏ HF PRO ✓) ⇒ nếu thuê VPS ở Linux thì **cài Colab CLI trên VPS đó** ⇒ 1 máy làm cả 2 việc ✓✓.

---

## 6. NHIỀU TÀI KHOẢN GOOGLE (user có ~5 acc, mỗi acc ~5h GPU/ngày ⇒ **~25h GPU/ngày**)

### 6.1 Vì sao làm được
`google-colab-cli` lưu **token OAuth ở đường dẫn HARDCODE global**:
`~/.config/colab-cli/token.json` (source `auth.py:54`) ⇒ **mỗi tài khoản = 1 bộ token riêng** ⇒
`scripts/colab_accounts.py` **swap token** (copy token acc → global trước khi gọi CLI, copy ngược lại sau ✓).

Cấu trúc:
```
scripts/colab_accounts/acc1..acc5/
    sessions.json   <- trạng thái session của acc đó
    token.json      <- token OAuth của acc đó
```

### 6.2 Quy trình (1 lần cho mỗi acc)
```powershell
python scripts\colab_accounts.py init 5              # tạo thư mục config
# Với TỪNG acc (2..5): user LOGOUT Google (hoặc dùng cửa sổ ẩn danh)
python scripts\colab_accounts.py login 2              # CLI mở trình duyệt -> user chọn acc2
python scripts\colab_accounts.py login 3              # ... lặp cho acc3..5
python scripts\colab_accounts.py status               # xem quota + session từng acc
```
> `login` chạy lệnh CLI ⇒ **trình duyệt mở** ⇒ user đăng nhập bằng acc đó ⇒ token được **copy vào `accN/token.json`** ✓ ⇒ từ đó dùng acc đó qua wrapper ✓.

### 6.3 Chạy 1 job trên 1 acc
```powershell
python scripts\colab_accounts.py run 2 --gpu T4       # cấp session trên acc2
python scripts\colab_accounts.py stop 2               # giải tài nguyên
```
Chạy code trên VM (file .py **UTF-8 không BOM** ✓):
```powershell
colab --config scripts\colab_accounts\acc2\sessions.json `
      -c scripts\colab_accounts\acc2\oauth.json exec -s orn-t4 -f train.py
```
Tải kết quả về: `colab download -s <session> /content/work/gui_lora ./out` ✓.

### 6.4 Quy mô & giới hạn
| hạng mục | giá trị |
|---|---|
| Tổng GPU/ngày | 5 acc × ~5h = **~25h** ✓ (nhiều hơn Kaggle 30h/tuần ✗ đã hết ✓) |
| GPU | T4 16GB ⇒ **4-bit QLoRA** ⇒ số liệu **không so sánh được** với bf16 Kaggle ✗ ⇒ dùng cho **train thử/so sánh nội bộ** ✓; muốn bf16 ⇒ **Colab Pro (A100/L4)** ✓ |
| Upload file | **endpoint `contents` của Colab đang trả 500** ✗ ⇒ **tránh `colab upload`** ✗ ⇒ **ĐÃ GIẢI QUYẾT (✓): host data trên HF dataset repo PUBLIC** → `scripts/hf_host_data.py --repo kkouadn/ornith-colab-data <file.zip>` ✓ ⇒ VM tải bằng `wget https://huggingface.co/datasets/kkouadn/ornith-colab-data/resolve/main/<file>.zip` ✓ (**không cần token** ✓ — đã test HTTP 206 + magic ZIP ✓) |
| Bảo mật | token của 5 acc nằm trong `scripts/colab_accounts/accN/token.json` ⇒ **KHÔNG commit** ✓ (repo này không push git ✓) |

### 6.5 Việc cần làm tiếp
1. User đăng nhập acc2..5 (mỗi acc 1 lần ✓).
2. Host `desktop-replay` + các `.zip` dataset trên **Space tĩnh** ⇒ VM tải bằng `wget` ✓ (tránh endpoint upload 500 ✓).
3. Chạy **train v25 (4-bit trên T4)** trên 5 acc song song ⇒ so sánh 5 biến thể recipe/seed trong 1 ngày ✓ (thay vì 1 biến thể/ngày trên Kaggle ✓).
4. Smoke-test GRPO (đang chạy ✓) → nếu PASS ⇒ chạy GRPO-v2 trên 5 acc ✓.
