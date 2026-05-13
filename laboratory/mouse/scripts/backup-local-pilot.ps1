param(
  [string]$ProjectRoot = "",
  [string]$BackupRoot = "",
  [string]$Label = "pilot"
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectRoot {
  param([string]$Value)
  if ($Value) {
    return (Resolve-Path -LiteralPath $Value).Path
  }
  $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
  return (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
}

function Resolve-BackupRoot {
  param([string]$Value)
  if ($Value) {
    if (-not (Test-Path -LiteralPath $Value)) {
      New-Item -ItemType Directory -Path $Value | Out-Null
    }
    return (Resolve-Path -LiteralPath $Value).Path
  }
  $base = $env:LOCALAPPDATA
  if (-not $base) {
    $base = Join-Path $env:USERPROFILE "AppData\Local"
  }
  $path = Join-Path $base "MouseDB\pilot-backups"
  if (-not (Test-Path -LiteralPath $path)) {
    New-Item -ItemType Directory -Path $path | Out-Null
  }
  return (Resolve-Path -LiteralPath $path).Path
}

function Copy-IfExists {
  param(
    [string]$Source,
    [string]$Destination
  )
  if (Test-Path -LiteralPath $Source) {
    $parent = Split-Path -Parent $Destination
    if (-not (Test-Path -LiteralPath $parent)) {
      New-Item -ItemType Directory -Path $parent | Out-Null
    }
    Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
    return $true
  }
  return $false
}

$resolvedProjectRoot = Resolve-ProjectRoot -Value $ProjectRoot
$resolvedBackupRoot = Resolve-BackupRoot -Value $BackupRoot
$safeLabel = ($Label -replace "[^A-Za-z0-9._-]", "-").Trim("-")
if (-not $safeLabel) {
  $safeLabel = "pilot"
}
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $resolvedBackupRoot "$timestamp-$safeLabel"
New-Item -ItemType Directory -Path $backupPath | Out-Null

$items = @(
  @{ Source = "data\mouse_lims.sqlite"; Destination = "data\mouse_lims.sqlite"; Boundary = "canonical structured state / local pilot copy" },
  @{ Source = "data\photos"; Destination = "data\photos"; Boundary = "raw source / local pilot copy" },
  @{ Source = "data\exports"; Destination = "data\exports"; Boundary = "export or view / local pilot copy" },
  @{ Source = "mousedb_artifacts"; Destination = "mousedb_artifacts"; Boundary = "export or view / local pilot copy" }
)

$copied = @()
$missing = @()
foreach ($item in $items) {
  $source = Join-Path $resolvedProjectRoot $item.Source
  $destination = Join-Path $backupPath $item.Destination
  if (Copy-IfExists -Source $source -Destination $destination) {
    $copied += [ordered]@{
      source = $item.Source
      boundary = $item.Boundary
    }
  } else {
    $missing += [ordered]@{
      source = $item.Source
      boundary = $item.Boundary
    }
  }
}

$manifest = [ordered]@{
  layer = "export or view"
  canonical = $false
  created_at = (Get-Date).ToString("o")
  project_root = $resolvedProjectRoot
  backup_path = $backupPath
  copied = $copied
  missing = $missing
  restore_command = "powershell -ExecutionPolicy Bypass -File scripts/restore-local-pilot.ps1 -BackupPath `"$backupPath`" -TargetRoot `"$resolvedProjectRoot`" -Force"
}

$manifestPath = Join-Path $backupPath "backup-manifest.json"
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8

$manifest | ConvertTo-Json -Depth 8
