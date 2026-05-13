param(
  [Parameter(Mandatory = $true)]
  [string]$BackupPath,
  [string]$TargetRoot = "",
  [switch]$Force
)

$ErrorActionPreference = "Stop"

function Resolve-TargetRoot {
  param([string]$Value)
  if ($Value) {
    if (-not (Test-Path -LiteralPath $Value)) {
      New-Item -ItemType Directory -Path $Value | Out-Null
    }
    return (Resolve-Path -LiteralPath $Value).Path
  }
  $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
  return (Resolve-Path -LiteralPath (Join-Path $scriptDir "..")).Path
}

function Restore-IfExists {
  param(
    [string]$Source,
    [string]$Destination,
    [bool]$AllowOverwrite
  )
  if (-not (Test-Path -LiteralPath $Source)) {
    return "missing"
  }
  if ((Test-Path -LiteralPath $Destination) -and -not $AllowOverwrite) {
    throw "Refusing to overwrite existing restore target without -Force: $Destination"
  }
  $parent = Split-Path -Parent $Destination
  if (-not (Test-Path -LiteralPath $parent)) {
    New-Item -ItemType Directory -Path $parent | Out-Null
  }
  if (Test-Path -LiteralPath $Destination) {
    Remove-Item -LiteralPath $Destination -Recurse -Force
  }
  Copy-Item -LiteralPath $Source -Destination $Destination -Recurse -Force
  return "restored"
}

$resolvedBackupPath = (Resolve-Path -LiteralPath $BackupPath).Path
$resolvedTargetRoot = Resolve-TargetRoot -Value $TargetRoot
$manifestPath = Join-Path $resolvedBackupPath "backup-manifest.json"
if (-not (Test-Path -LiteralPath $manifestPath)) {
  throw "Backup manifest not found: $manifestPath"
}

$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ($manifest.layer -ne "export or view" -or $manifest.canonical -ne $false) {
  throw "Backup manifest boundary is invalid or missing."
}

$items = @(
  "data\mouse_lims.sqlite",
  "data\photos",
  "data\exports",
  "mousedb_artifacts"
)

$results = @()
foreach ($item in $items) {
  $source = Join-Path $resolvedBackupPath $item
  $destination = Join-Path $resolvedTargetRoot $item
  $status = Restore-IfExists -Source $source -Destination $destination -AllowOverwrite $Force.IsPresent
  $results += [ordered]@{
    path = $item
    status = $status
  }
}

[ordered]@{
  layer = "export or view"
  canonical = $false
  restored_at = (Get-Date).ToString("o")
  backup_path = $resolvedBackupPath
  target_root = $resolvedTargetRoot
  force = $Force.IsPresent
  results = $results
} | ConvertTo-Json -Depth 8
