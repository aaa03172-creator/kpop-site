param(
  [string]$TargetTriple = "",
  [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not $Python) {
  $venvPython = Join-Path $Root ".venv\Scripts\python.exe"
  if (Test-Path $venvPython) {
    $Python = $venvPython
  } else {
    $Python = "python"
  }
}

& $Python -m pip install --disable-pip-version-check -r requirements.txt

if (-not $TargetTriple) {
  try {
    $TargetTriple = (& rustc --print host-tuple).Trim()
  } catch {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
      $TargetTriple = "x86_64-pc-windows-msvc"
    } else {
      throw "Unable to determine target triple. Install Rust or pass -TargetTriple."
    }
  }
}

& $Python -m PyInstaller desktop\pyinstaller\mousedb-server.spec --noconfirm --clean

$binaryDir = Join-Path $Root "src-tauri\binaries"
New-Item -ItemType Directory -Force -Path $binaryDir | Out-Null

$sourceExe = Join-Path $Root "dist\mousedb-server.exe"
if (-not (Test-Path $sourceExe)) {
  throw "Expected PyInstaller output missing: $sourceExe"
}

$targetExe = Join-Path $binaryDir "mousedb-server-$TargetTriple.exe"
Copy-Item -LiteralPath $sourceExe -Destination $targetExe -Force
Write-Host "Built desktop sidecar: $targetExe"
