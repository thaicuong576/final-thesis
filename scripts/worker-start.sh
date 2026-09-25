#!/usr/bin/env bash
set -e

BRANCH_NAME=$1

if [ -z "$BRANCH_NAME" ]; then
  echo "❌ Error: Thieu ten branch."
  echo "Usage: bash scripts/worker-start.sh feat/<domain>-<task-name>"
  exit 1
fi

REPO_ROOT=$(pwd)
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
DIR_SAFE_NAME="${BRANCH_NAME//\//-}"
WORKTREE_PATH=".worktrees/$DIR_SAFE_NAME"

echo "🌱 Fetching remote origin/main..."
git fetch origin main

echo "🚀 Khoi tao Git Worktree tai: $WORKTREE_PATH..."
git worktree add -b "$BRANCH_NAME" "$WORKTREE_PATH" origin/main

echo "🔗 Ke thua Local State va Runtime configs..."

if [ -f "$REPO_ROOT/.env" ]; then
  ln -f "$REPO_ROOT/.env" "$WORKTREE_PATH/.env" 2>/dev/null || cp "$REPO_ROOT/.env" "$WORKTREE_PATH/.env"
fi

if [ -d "$REPO_ROOT/.venv" ]; then
  ln -s "$REPO_ROOT/.venv" "$WORKTREE_PATH/.venv" 2>/dev/null || cp -r "$REPO_ROOT/.venv" "$WORKTREE_PATH/.venv" 2>/dev/null || true
fi

# Create an independent SQLite snapshot for the worktree. Never hardlink or
# symlink the mutable database or its WAL/SHM sidecars back to the root repo.
DB_DIR="$REPO_ROOT/data/processed"
WORKTREE_DB_DIR="$WORKTREE_PATH/data/processed"
if [ -f "$DB_DIR/finance_master_v2.sqlite" ]; then
  mkdir -p "$WORKTREE_DB_DIR"
  PYTHON_BIN="${PYTHON:-python}"
  "$PYTHON_BIN" "$SCRIPT_DIR/copy_sqlite_snapshot.py" \
    --source "$DB_DIR/finance_master_v2.sqlite" \
    --destination "$WORKTREE_DB_DIR/finance_master_v2.sqlite"
fi

if [ -d "$REPO_ROOT/frontend/node_modules" ]; then
  mkdir -p "$WORKTREE_PATH/frontend"
  ln -s "$REPO_ROOT/frontend/node_modules" "$WORKTREE_PATH/frontend/node_modules" 2>/dev/null || true
fi

echo "✅ Worktree da san sang!"
echo "👉 Chuyen context lam viec: cd $WORKTREE_PATH"
