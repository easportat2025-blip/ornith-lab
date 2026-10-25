# auto-gen by gen_post_gate.py - post-action cho khoadangnguye/ornith-gui-bench-v14-v21
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\post_gate.ps1' `
    -Kernel 'khoadangnguye/ornith-gui-bench-v14-v21' -Out 'phase13-gui/out_bench_v14_v21' -Label 'v21'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
