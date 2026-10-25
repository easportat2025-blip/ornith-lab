# auto-gen by gen_post_gate.py - post-action cho dieniw/ornith-bench-3d-b1
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'
Set-Location 'C:\Users\Admin\Desktop\New folder'
& powershell -NoProfile -ExecutionPolicy Bypass -File 'scripts\post_gate.ps1' `
    -Kernel 'dieniw/ornith-bench-3d-b1' -Out 'phase13-gui/out_bench_3d_B' -Label 'v18-3D'
Write-Output ("POST-RC " + $LASTEXITCODE)
exit 0
