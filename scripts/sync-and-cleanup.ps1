param (
    [Parameter(Mandatory = $false)]
    [string]$BranchName
)

$ErrorActionPreference = "Continue"

Write-Host "[SYNC] Synchronizing local main with origin/main..." -ForegroundColor Cyan
git checkout main
git pull origin main

if ($BranchName) {
    $DirSafeName = $BranchName -replace '/', '-'
    $WorktreePath = ".worktrees\$DirSafeName"

    Write-Host "[CLEANUP] Removing worktree: $WorktreePath..." -ForegroundColor Cyan
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
    Write-Host "[OK] Cleaned up branch $BranchName and worktree." -ForegroundColor Green
}
