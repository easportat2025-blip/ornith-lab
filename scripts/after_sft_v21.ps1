# after_sft_v21.ps1 - sau khi kernel SFT v21 COMPLETE:
#   tai adapter -> upload dataset lora-v21 -> wait READY -> push bench B15 v21 + bench v14 v21
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== post v21 adapter $(Get-Date -Format 'HH:mm:ss') ===")
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\post_v21_adapter.ps1
$rc = $LASTEXITCODE
Write-Output ("ADAPTER-EXIT " + $rc)
if ($rc -ne 0) { Write-Output 'adapter chua san sang - dung, khong push bench'; exit 1 }

# KHONG push kernel o day: cac kernel gate do scripts/gpu_queue.json tu push
# (hang doi GPU tu dong, ton trong nhip <= 2 session + quota con).
Write-Output ("DONE (dataset lora-v21 da READY -> gpu_queue se push gate) " + (Get-Date -Format 'HH:mm:ss'))
