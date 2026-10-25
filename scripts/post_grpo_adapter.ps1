# post_grpo_adapter.ps1 - sau khi kernel GRPO-v1 COMPLETE (acc B):
#   1) tai adapter gui_lora/ + grpo_result.json
#   2) stage + upload dataset `dieniw/ornith-gui-lora-grpo1` (cho gate)
#   3) tao kernel gate cho adapter GRPO (B15,5 + B16-A + desktop) va dua vao queue B
# KHONG push kernel gate (watchdog lo). Neu kernel bi cat giua chung, adapter
# duoc luu tu checkpoint-* nen van dung duoc.
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai adapter GRPO $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels output dieniw/ornith-gui-grpo-v1 -p phase13-gui/out_grpo_v1 --file-pattern "gui_lora/.*|grpo_result.json" --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

if (-not (Test-Path 'phase13-gui/out_grpo_v1/gui_lora/adapter_config.json')) {
  Write-Output 'THIEU adapter_config.json - GRPO khong xong (ho bi cat quota)'
  exit 1
}

$stage = 'phase13-gui/lora_grpo1_dataset'
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Get-ChildItem 'phase13-gui/out_grpo_v1/gui_lora/*' | Copy-Item -Destination $stage -Force -Recurse
@'
{"title": "Ornith GUI LoRA GRPO v1 (reward verifiable)", "id": "dieniw/ornith-gui-lora-grpo1", "licenses": [{"name": "other"}]}
'@ | Set-Content -Path "$stage/dataset-metadata.json" -Encoding ascii

Write-Output '=== upload adapter GRPO len acc B ==='
kaggle datasets create -p $stage
kaggle datasets version -p $stage -m "grpo v1 adapter" 2>&1 | Select-Object -Last 2

Write-Output '=== tao kernel gate cho adapter GRPO ==='
python scripts\make_grpo_bench_kernels.py

Write-Output '=== xong post_grpo ==='
