#!/bin/bash
# Read first available ops secret from deployed .env (safe for cron — no export required).
mn2_read_ops_secret() {
  local env="${MN2_ENV_FILE:-/var/www/html/.env}"
  local key val
  [ -f "$env" ] || return 1
  for key in MN2_OPS_SECRET DISCORD_OPS_SECRET ADMIN_OPS_SECRET MN2_SCAN_SECRET; do
    val=$(grep "^${key}=" "$env" 2>/dev/null | head -1 | cut -d= -f2- | tr -d '\r"') || true
    if [ -n "${val:-}" ]; then
      printf '%s' "$val"
      return 0
    fi
  done
  return 1
}
