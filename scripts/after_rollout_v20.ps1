# after_rollout_v20.ps1 - rollout-v20 xong -> day GPU slot -> chay baseline
# B15.5 voi adapter v18 (khong contaminate, tien do deu).
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'

$st = (kaggle datasets status khoadangnguye/ornith-gui-bench-v155 2>&1 | Out-String)
if ($st -notmatch 'ready|active') {
  Write-Output ("dataset chua READY: " + ($st -replace "`r?`n", ' '))
  exit 1
}
Write-Output ("=== push bench B15 think0 (thi nghiem lever C1) $(Get-Date -Format 'HH:mm:ss') ===")
kaggle kernels push -p phase13-gui/kernel_bench_v18_think0
Write-Output ("PUSH-EXIT " + $LASTEXITCODE + " $(Get-Date -Format 'HH:mm:ss')")
