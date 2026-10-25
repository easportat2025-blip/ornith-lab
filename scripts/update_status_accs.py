"""update_status_accs.py - cap nhat STATUS.md voi trang thai 2 acc + 4 bai hoc CLI."""
import io

P = 'STATUS.md'
s = io.open(P, encoding='utf-8').read()
OLD_START = "## 0. Tai khoan & GPU (20/10 12:05) - **ACC CHINH = `khoadangnguye`**"
NEW = """## 0. Tai khoan & GPU (20/10 13:40) - **2 ACC, 60 GPU-GIO**

| Acc | Quota GPU | Vai tro |
|---|---|---|
| **`khoadangnguye` (A)** | 1.1h/30h | train v21 + cac gate cua v21 + rollout v21 (queue `gpu_queue.json`, 9 muc) |
| **`dieniw` (B)** | 0.01h/30h | baseline v18 (B15.5/B16/3D) + train v22 + gate v22 (queue `gpu_queue_B.json`, 8 muc) |
| `hhjiji` | het (reset thu Bay 24/10) | giu dataset goc (khong chay GPU) |

- **Key chi truyen qua env var** (`KAGGLE_USERNAME`/`KAGGLE_KEY`), **khong ghi file**.
- **Dataset private theo acc** -> acc khac khong mount duoc -> moi dataset phai **ferry** sang acc dich (`scripts/ferry_dataset.py`).
- `kaggle kernels push` lay repo id **TU metadata** -> muon chay tren acc B phai co bien thep kernel rieng (`*_B/`, doi namespace trong metadata).
- Watchdog: 2 process doc queue tu env `GPU_QUEUE`; state file rieng; **check quota 1 lan/ngay** + len lich dung luc `refreshAt`; **CREATE_NO_WINDOW** (khong con cua so den).

### 4 bai hoc Kaggle CLI (da ton GPU-gio)
1. `datasets create/version` **BO QUA THU MUC** (chi lay file o cap goc) -> dataset co `deps_out/`/`shots/`/`images/` bi upload **RONG, KHONG BAO LOI**.
2. CLI tra **exit code 0 KE CA khi API loi (403/404)** -> phai kiem **CHUOI output**, khong tin rc.
3. `datasets download` tra 1 file `.zip` chua giai nen -> upload **NGUYEN file zip** do (Kaggle tu giai nen, giu cau truc goc).
4. `kernels list` phan trang 20 dong -> de quet het dataset phai `--page-size 200` + `--page-token`.
"""
if OLD_START in s:
    i = s.index(OLD_START)
    j = s.index("## 8.", i)
    s = s[:i] + NEW + "\n" + s[j:]
    io.open(P, 'w', encoding='utf-8', newline='').write(s)
    print("STATUS.md: cap nhat muc acc")
else:
    print("khong tim thay muc can cap nhat")
