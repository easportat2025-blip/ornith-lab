$env:PYTHONIOENCODING = 'utf-8'
Set-Location 'C:\Users\Admin\Desktop\New folder'
$src = 'phase13-gui/out_v20/gui_lora'

if (-not (Test-Path "$src/adapter_config.json")) {
  Write-Output "CHUA CO ADAPTER tai $src - chay lai sau khi poller tai xong"
  exit 1
}

# copy adapter (flat files) vao staging roi upload
Copy-Item "$src\*" -Destination 'phase13-gui/lora_v20_dataset\' -Force -Recurse
Write-Output "=== copy xong, file list ==="
Get-ChildItem 'phase13-gui/lora_v20_dataset' | Select-Object Name, Length

New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:TEMP\.kaggle\uploads\phase13-gui" | Out-Null
Write-Output "=== upload $(Get-Date -Format 'HH:mm:ss') ==="
kaggle datasets create -p 'C:\Users\Admin\Desktop\New folder\phase13-gui\lora_v20_dataset'
$code = $LASTEXITCODE
if ($code -ne 0) {
  Write-Output "create loi (co the da ton tai) -> thu version"
  kaggle datasets version -p 'C:\Users\Admin\Desktop\New folder\phase13-gui\lora_v20_dataset' -m "lora v20 update $(Get-Date -Format 'HH:mm')"
  $code = $LASTEXITCODE
}
Write-Output ("UPLOAD-EXIT " + $code + " $(Get-Date -Format 'HH:mm:ss')")
