# kq.ps1 - goi kaggle CLI KHONG mo cua so den (CreateNoWindow).
# Dung:  powershell -NoProfile -File scripts\kq.ps1 quota
#        powershell -NoProfile -File scripts\kq.ps1 kernels status hhjiji/xxx
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "kaggle"
$psi.Arguments = ($args -join ' ')
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true
$psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
$psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
$p = New-Object System.Diagnostics.Process
$p.StartInfo = $psi
[void]$p.Start()
$out = $p.StandardOutput.ReadToEnd()
$err = $p.StandardError.ReadToEnd()
$p.WaitForExit()
if ($out) { Write-Output $out }
if ($err) { Write-Output $err }
exit $p.ExitCode
