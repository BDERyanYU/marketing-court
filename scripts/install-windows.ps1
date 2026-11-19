$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$installRoot = Join-Path $env:LOCALAPPDATA 'MarketingCourt'
if (-not (Test-Path -LiteralPath (Join-Path $installRoot 'Start-Windows.cmd'))) {
    Write-Host '正在下载 Marketing Court……'
    $downloadRoot = Join-Path ([IO.Path]::GetTempPath()) ('marketing-court-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $downloadRoot -Force | Out-Null
    $archive = Join-Path $downloadRoot 'project.zip'
    Invoke-WebRequest -UseBasicParsing 'https://github.com/BDERyanYU/marketing-court/archive/refs/heads/main.zip' -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $downloadRoot
    Move-Item -LiteralPath (Join-Path $downloadRoot 'marketing-court-main') -Destination $installRoot
    Remove-Item -LiteralPath $archive
}
$desktop = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $desktop 'Marketing Court.lnk'))
$shortcut.TargetPath = Join-Path $installRoot 'Start-Windows.cmd'
$shortcut.WorkingDirectory = $installRoot
$shortcut.Save()
Write-Host '以后双击桌面的 Marketing Court 即可打开。'
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $installRoot 'scripts/launch-windows.ps1')
if ($LASTEXITCODE -ne 0) { throw '启动未完成，请查看上方提示。' }
