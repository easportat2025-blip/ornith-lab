param(
  [Parameter(Mandatory=$true)][string]$Kernel,
  [Parameter(Mandatory=$true)][string]$OutDir,
  [string]$FilePattern = ".*",
  [int]$IntervalSec = 90,
  [int]$MaxRounds = 40
)
$env:PYTHONIOENCODING = "utf-8"
Set-Location "C:\Users\Admin\Desktop\New folder"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
for ($i = 1; $i -le $MaxRounds; $i++) {
  $status = (& kaggle kernels status $Kernel 2>&1 | Out-String).Trim()
  Write-Output ("[{0}] {1} round {2}: {3}" -f (Get-Date -Format "HH:mm:ss"), $Kernel, $i, $status)
  if ($status -match 'KernelWorkerStatus\.(COMPLETE|ERROR|CANCEL)') {
    Write-Output ("DOWNLOAD {0}" -f (Get-Date -Format "HH:mm:ss"))
    & kaggle kernels output $Kernel -p $OutDir --file-pattern $FilePattern --force 2>&1 | Out-String | Write-Output
    Write-Output ("DOWNLOAD-DONE {0} exit={1}" -f (Get-Date -Format "HH:mm:ss"), $LASTEXITCODE)
    exit 0
  }
  Start-Sleep -Seconds $IntervalSec
}
Write-Output ("POLL-TIMEOUT {0}" -f (Get-Date -Format "HH:mm:ss"))
exit 1
