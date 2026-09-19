param (
    [Parameter(Mandatory = $true)]
    [string]$BranchName
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Location).Path
$DirSafeName = $BranchName -replace '/', '-'
$WorktreePath = Join-Path $RepoRoot ".worktrees\$DirSafeName"

Write-Host "🌱 Fetching remote origin/main..." -ForegroundColor Cyan
git fetch origin main

Write-Host "🚀 Khởi tạo Git Worktree tại: $WorktreePath..." -ForegroundColor Cyan
git worktree add -b $BranchName "$WorktreePath" origin/main

Write-Host "🔗 Kế thừa Local State và Runtime configs..." -ForegroundColor Cyan

if (Test-Path "$RepoRoot\.env") {
    Copy-Item "$RepoRoot\.env" "$WorktreePath\.env"
}

# Link real database finance_master_v2.sqlite
if (Test-Path "$RepoRoot\data\processed\finance_master_v2.sqlite") {
    $DestDir = "$WorktreePath\data\processed"
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    cmd /c mklink "$DestDir\finance_master_v2.sqlite" "$RepoRoot\data\processed\finance_master_v2.sqlite" 2>$null
    if (-not (Test-Path "$DestDir\finance_master_v2.sqlite")) {
        Copy-Item "$RepoRoot\data\processed\finance_master_v2.sqlite" "$DestDir\finance_master_v2.sqlite"
    }
}

# Link node_modules via Directory Junction
if (Test-Path "$RepoRoot\frontend\node_modules") {
    $FrontendDest = "$WorktreePath\frontend"
    New-Item -ItemType Directory -Force -Path $FrontendDest | Out-Null
    cmd /c mklink /J "$FrontendDest\node_modules" "$RepoRoot\frontend\node_modules" 2>$null
}

Write-Host "✅ Worktree đã sẵn sàng!" -ForegroundColor Green
Write-Host "👉 Chuyển context làm việc: cd $WorktreePath" -ForegroundColor Yellow
