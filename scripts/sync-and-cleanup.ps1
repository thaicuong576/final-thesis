param (
    [Parameter(Mandatory = $false)]
    [string]$BranchName
)

$ErrorActionPreference = "Continue"

Write-Host "🔄 Đồng bộ local main với origin/main..." -ForegroundColor Cyan
git checkout main
git pull origin main

if ($BranchName) {
    $DirSafeName = $BranchName -replace '/', '-'
    $WorktreePath = ".worktrees\$DirSafeName"

    Write-Host "🧹 Thu hồi và dọn dẹp worktree: $WorktreePath..." -ForegroundColor Cyan
    if (Test-Path $WorktreePath) {
        git worktree remove "$WorktreePath" --force 2>$null
        if (Test-Path $WorktreePath) {
            Remove-Item -Recurse -Force $WorktreePath -ErrorAction SilentlyContinue
        }
    }

    git branch -d $BranchName 2>$null
    if ($LASTEXITCODE -ne 0) {
        git branch -D $BranchName 2>$null
    }
    git worktree prune
    Write-Host "✨ Đã đóng hoàn toàn branch $BranchName và dọn dẹp worktree." -ForegroundColor Green
}
