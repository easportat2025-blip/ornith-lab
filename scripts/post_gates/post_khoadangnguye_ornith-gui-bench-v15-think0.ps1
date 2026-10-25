# auto-gen by gen_post_gate.py - post-action cho khoadangnguye/ornith-gui-bench-v15-think0
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\post_gate.ps1' `
    -Kernel 'khoadangnguye/ornith-gui-bench-v15-think0' -Out 'phase13-gui/out_bench_v18_think0' -Label 'v18-think0'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
