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
    cmd /c mklink /H "$WorktreePath\.env" "$RepoRoot\.env" 2>$null
    if (-not (Test-Path "$WorktreePath\.env")) {
        Copy-Item "$RepoRoot\.env" "$WorktreePath\.env"
    }
}

# Link real database finance_master_v2.sqlite and WAL files
$DbDir = "$RepoRoot\data\processed"
$DestDir = "$WorktreePath\data\processed"
if (Test-Path "$DbDir\finance_master_v2.sqlite") {
    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    $DbFiles = @("finance_master_v2.sqlite", "finance_master_v2.sqlite-wal", "finance_master_v2.sqlite-shm")
    foreach ($file in $DbFiles) {
        $srcFile = Join-Path $DbDir $file
        $dstFile = Join-Path $DestDir $file
        if (Test-Path $srcFile) {
            cmd /c mklink /H "$dstFile" "$srcFile" 2>$null
            if (-not (Test-Path "$dstFile")) {
                cmd /c mklink "$dstFile" "$srcFile" 2>$null
            }
            if (-not (Test-Path "$dstFile")) {
                Copy-Item "$srcFile" "$dstFile"
            }
        }
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
