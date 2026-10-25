"""prepend_status_acc.py - them muc 'Tai khoan & GPU' vao dau STATUS.md."""
import io

P = 'STATUS.md'
s = io.open(P, encoding='utf-8').read()
BLOCK = """## 0. Tai khoan & GPU (20/10 12:05) - **ACC CHINH = `khoadangnguye`**

| Acc | Trang thai |
|---|---|
| **`khoadangnguye` (acc A)** | GPU 0.04h/30.00h - dang chay `ornith-gui-sft-v21` (train) + hang doi 17 muc |
| `hhjiji` | het quota GPU (30.13h/30.00h) - reset **thu Bay 24/10** |
| `dieniw`, `phnguynh`, `kaggle_backup.json` | key chet (401) |

- **Key chi truyen qua env var** (`KAGGLE_USERNAME` / `KAGGLE_KEY`), **khong ghi file**.
- **Dataset private theo acc** -> acc khac khong mount duoc -> dataset moi phai **ferry** sang acc A (`scripts/ferry_dataset.py`) truoc khi kernel mount.
- Base shards `dieniw/ornbase-s1..4` + wheels la **public** -> mount cross-account binh thuong.
- Watchdog chay voi env acc A; **check quota 1 lan/ngay** + len lich dung luc `refreshAt`; cache 6h cho dashboard.

"""
if '## 0. Tai khoan & GPU' not in s:
    io.open(P, 'w', encoding='utf-8', newline='').write(BLOCK + s)
    print('STATUS.md: them muc acc')
else:
    print('da co')
