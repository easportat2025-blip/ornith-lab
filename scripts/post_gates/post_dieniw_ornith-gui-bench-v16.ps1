# auto-gen by gen_post_gate.py - post-action cho dieniw/ornith-gui-bench-v16
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\post_gate.ps1' `
    -Kernel 'dieniw/ornith-gui-bench-v16' -Out 'phase13-gui/out_bench_v16_B' -Label 'v18-base'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
