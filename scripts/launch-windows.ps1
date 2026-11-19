$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$toolsRoot = Join-Path $projectRoot 'data/launcher'
New-Item -ItemType Directory -Path $toolsRoot -Force | Out-Null
$uvRoot = Join-Path $toolsRoot 'uv'
$uvExe = Join-Path $uvRoot 'uv.exe'
if (-not (Test-Path -LiteralPath $uvExe)) {
    Write-Host '正在准备启动工具，首次运行需要联网……'
    # The OCR wheel uses x64; Windows 11 ARM can run the same x64 toolchain.
    $arch = 'x86_64'
    $sha = '9ee74df98582f37fdd6069e1caac80d2616f9a489f5dbb2b1c152f30be69c58e'
    $archive = Join-Path $toolsRoot 'uv.zip'
    Invoke-WebRequest -UseBasicParsing "https://github.com/astral-sh/uv/releases/download/0.10.11/uv-$arch-pc-windows-msvc.zip" -OutFile $archive
    if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sha) { throw '启动工具校验失败，请重试。' }
    Expand-Archive -LiteralPath $archive -DestinationPath $uvRoot -Force
    Remove-Item -LiteralPath $archive
}
$env:UV_PYTHON_INSTALL_DIR = Join-Path $toolsRoot 'python'
$env:UV_CACHE_DIR = Join-Path $toolsRoot 'uv-cache'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
& $uvExe run --python cpython-3.12-windows-x86_64-none --no-project (Join-Path $PSScriptRoot 'launch.py') --uv $uvExe @args
exit $LASTEXITCODE
