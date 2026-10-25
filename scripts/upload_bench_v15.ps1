$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\Admin\Desktop\New folder'
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null

Write-Output "=== build zip $(Get-Date -Format 'HH:mm:ss') ==="
python phase13-gui/bench_dataset/build_bench_zip.py
if ($LASTEXITCODE -ne 0) { Write-Output "ZIP FAILED"; exit 1 }

Write-Output "=== upload dataset $(Get-Date -Format 'HH:mm:ss') ==="
kaggle datasets create -p phase13-gui/bench_dataset
Write-Output ("UPLOAD-EXIT " + $LASTEXITCODE + " $(Get-Date -Format 'HH:mm:ss')")
