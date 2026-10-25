# auto-gen cho gate v22
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\post_gate.ps1' `
    -Kernel 'khoadangnguye/ornith-gui-bench-v155-v22' -Out 'phase13-gui/out_bench_v155_v22' -Label 'v22'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
