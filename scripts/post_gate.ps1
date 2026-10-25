# post_gate.ps1 - sau khi kernel bench COMPLETE: tai output + cham gate + ghi LOBBY.
# Dung:  powershell -File scripts/post_gate.ps1 -Kernel <id> -Out <dir> -Label <v21>
# Key lay tu env cua tiem trinh (watchdog truyen san) - KHONG ghi key vao file.
param(
  [string]$Kernel = 'khoadangnguye/ornith-gui-bench-v21',
  [string]$Out = 'phase13-gui/out_bench_v21',
  [string]$Label = 'v21',
  [int]$HoldoutVariant = 2,
  [string]$Pattern = '.*result\.json|.*summary\.json'
)
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

Write-Output ("=== tai output $Kernel -> $Out ($(Get-Date -Format 'HH:mm:ss')) ===")
New-Item -ItemType Directory -Force -Path $Out | Out-Null
kaggle kernels output $Kernel -p $Out --file-pattern $Pattern --force
Write-Output ("DOWNLOAD-EXIT " + $LASTEXITCODE)

Write-Output '=== cham gate ==='
python scripts/post_gate.py --out $Out --label $Label --kernel $Kernel --holdout-variant $HoldoutVariant
Write-Output ("GATE-RC " + $LASTEXITCODE)
exit 0
