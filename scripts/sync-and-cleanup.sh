#!/usr/bin/env bash
set -e

BRANCH_NAME=$1
REPO_ROOT=$(pwd)

echo "🔄 Dong bo local main voi origin/main..."
git checkout main
git pull origin main

if [ -n "$BRANCH_NAME" ]; then
  DIR_SAFE_NAME="${BRANCH_NAME//\//-}"
  WORKTREE_PATH=".worktrees/$DIR_SAFE_NAME"

  echo "🧹 Thu hoi va don dep worktree: $WORKTREE_PATH..."
  if [ -d "$WORKTREE_PATH" ]; then
    git worktree remove "$WORKTREE_PATH" --force 2>/dev/null || rm -rf "$WORKTREE_PATH"
  fi

  git branch -d "$BRANCH_NAME" 2>/dev/null || git branch -D "$BRANCH_NAME" 2>/dev/null || true
  git worktree prune
  echo "✨ Da dong hoan toan branch $BRANCH_NAME va don dep worktree."
fi
