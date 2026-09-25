param (
    [Parameter(Mandatory = $true)]
    [string]$BranchName
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Location).Path
$DirSafeName = $BranchName -replace '/', '-'
$WorktreePath = Join-Path $RepoRoot ".worktrees\$DirSafeName"

Write-Host "[INIT] Fetching remote origin/main..." -ForegroundColor Cyan
git fetch origin main

Write-Host "[INIT] Creating Git Worktree at: $WorktreePath..." -ForegroundColor Cyan
git worktree add -b $BranchName "$WorktreePath" origin/main

Write-Host "[LINK] Linking local state and runtime configs..." -ForegroundColor Cyan

if (Test-Path "$RepoRoot\.env") {
    cmd /c mklink /H "$WorktreePath\.env" "$RepoRoot\.env" 2>$null
    if (-not (Test-Path "$WorktreePath\.env")) {
        Copy-Item "$RepoRoot\.env" "$WorktreePath\.env"
    }
}

# Create an independent SQLite snapshot for the worktree. Never hardlink the
# mutable database or its WAL/SHM sidecars: a test or local API write through a
# hardlink would mutate the root data artifact and every other worktree.
$DbDir = "$RepoRoot\data\processed"
$DestDir = "$WorktreePath\data\processed"
if (Test-Path "$DbDir\finance_master_v2.sqlite") {
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    $SourceDb = Join-Path $DbDir "finance_master_v2.sqlite"
    $DestinationDb = Join-Path $DestDir "finance_master_v2.sqlite"
    $SnapshotHelper = Join-Path $PSScriptRoot "copy_sqlite_snapshot.py"
    & python $SnapshotHelper --source "$SourceDb" --destination "$DestinationDb"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $DestinationDb)) {
        throw "Failed to create an isolated SQLite snapshot for the worktree."
    }
}

# Link node_modules via Directory Junction
if (Test-Path "$RepoRoot\frontend\node_modules") {
    $FrontendDest = "$WorktreePath\frontend"
    New-Item -ItemType Directory -Force -Path $FrontendDest | Out-Null
    cmd /c mklink /J "$FrontendDest\node_modules" "$RepoRoot\frontend\node_modules" 2>$null
}

Write-Host "[OK] Worktree is ready!" -ForegroundColor Green
Write-Host "[CONTEXT] Switch directory: cd $WorktreePath" -ForegroundColor Yellow
