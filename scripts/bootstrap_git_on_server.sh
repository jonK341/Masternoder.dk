#!/usr/bin/env bash
# One-time: make /var/www/html a git checkout of origin/main (no prior git required).
# Run ON THE SERVER as root (or user that owns the app tree):
#   curl -fsSL "https://raw.githubusercontent.com/jonK341/Masternoder.dk/main/scripts/bootstrap_git_on_server.sh" | bash  <!-- pragma: allowlist secret -->
# Or save and run: bash bootstrap_git_on_server.sh
set -euo pipefail

REMOTE_BASE="${REMOTE_BASE:-/var/www/html}"
ORIGIN="${GIT_ORIGIN:-https://github.com/jonK341/Masternoder.dk.git}"  <!-- pragma: allowlist secret -->
BRANCH="${GIT_BRANCH:-main}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_DIR:-/root/html-git-bootstrap-$STAMP}"

echo "=== bootstrap git on server ==="
echo "REMOTE_BASE=$REMOTE_BASE"
echo "ORIGIN=$ORIGIN"
echo "BRANCH=$BRANCH"

if ! command -v git >/dev/null 2>&1; then
  echo "ERROR: git is not installed. On Debian/Ubuntu run: apt update && apt install -y git"
  exit 1
fi

if [ ! -d "$REMOTE_BASE" ]; then
  echo "ERROR: $REMOTE_BASE does not exist."
  exit 1
fi

cd "$REMOTE_BASE"

if [ -d .git ]; then
  echo "Already a git repo. Remotes:"
  git remote -v || true
  echo "Try: cd $REMOTE_BASE && git pull --ff-only origin $BRANCH"
  exit 0
fi

mkdir -p "$BACKUP_DIR"
echo "Backing up .env and local state to $BACKUP_DIR ..."
[ -f .env ] && cp -a .env "$BACKUP_DIR/.env"
[ -d data ] && cp -a data "$BACKUP_DIR/data" 2>/dev/null || true
[ -d logs ] && cp -a logs "$BACKUP_DIR/logs" 2>/dev/null || true
[ -d instance ] && cp -a instance "$BACKUP_DIR/instance" 2>/dev/null || true

echo "Initializing git and fetching $BRANCH ..."
git init
git remote add origin "$ORIGIN"
git fetch origin "$BRANCH"

echo "Aligning working tree to origin/$BRANCH (tracked files only) ..."
git checkout -B "$BRANCH" "origin/$BRANCH" -f

echo "Restoring .env from backup if we had one ..."
if [ -f "$BACKUP_DIR/.env" ]; then
  cp -a "$BACKUP_DIR/.env" .env
  echo "  .env restored"
fi

echo "Setting upstream for future pulls ..."
git branch --set-upstream-to="origin/$BRANCH" "$BRANCH" 2>/dev/null || true

echo
echo "=== SUCCESS ==="
echo "You are now on: $(git log -1 --oneline)"
echo "Routine deploy:"
echo "  cd $REMOTE_BASE"
echo "  git pull --ff-only origin $BRANCH"
echo "  bash scripts/production_apply_routes.sh"  # pragma: allowlist secret
echo "Backup kept at: $BACKUP_DIR"
