# kernel_bench_v15 — eval adapter trên suite B15 (reasoning 256, offline)

## Cách dùng
```powershell
$env:PYTHONIOENCODING="utf-8"
kaggle kernels push -p phase13-gui/kernel_bench_v15
kaggle kernels status hhjiji/ornith-gui-bench-v15   # verify ngay
```

## Biến thể (đổi `dataset_sources` + `id` trong kernel-metadata.json trước khi push)
- **Baseline v18** (hiện tại): adapter = `hhjiji/ornith-gui-lora`, id `hhjiji/ornith-gui-bench-v15`.
- **v20** (sau khi upload adapter): adapter = `hhjiji/ornith-gui-lora-v20`,
  id `hhjiji/ornith-gui-bench-v15-v20` (tạo bản sao dir này rồi sửa metadata;
  script y hệt).

## Phụ thuộc
- Suite B15: dataset `hhjiji/ornith-gui-bench-v15` (zip `bench_v15/`) — build bằng
  `phase13-gui/bench_dataset/build_bench_zip.py`, upload bằng
  `scripts/upload_bench_v15.ps1`. PHẢI có trước khi push (dataset chưa tồn tại
  → push fail).
- Offline browsers: `hhjiji/ornith-offline-browsers` (gate V1–V6 fail LOUD).
- Nếu suite thiếu → kernel tự chạy 3 task v14 (fallback) để không mất run.

## Hợp đồng suite (cho MiMo)
Module `bench_v15.py` | `checker.py` trong `bench_v15/` cần expose:
```python
def render_instruction(page, task_id, variant) -> str   # sau page.goto; đã thay placeholder
def check(page) -> dict  # {"success": bool, "reason": str, "state": {...}}
```
Ngoài ra: `document.body.dataset.*` của từng trang là nguồn state gốc.
