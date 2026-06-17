#!/usr/bin/env node
/**
 * MN2 wallet + explorer post-deploy smoke (fetch then browser).
 * Usage:
 *   node scripts/smoke_mn2_wallet_explorer.mjs
 *   node scripts/smoke_mn2_wallet_explorer.mjs --fetch-only
 *   node scripts/smoke_mn2_wallet_explorer.mjs --browser-only
 * Env: MN2_TEST_BASE, MN2_TEST_USER
 */
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const fetchOnly = args.includes('--fetch-only');
const browserOnly = args.includes('--browser-only');

function run(script) {
  console.log(`\n>>> ${script}\n`);
  const r = spawnSync(process.execPath, [join(__dir, script)], {
    stdio: 'inherit',
    env: process.env,
  });
  return r.status === 0;
}

let ok = true;
if (!browserOnly) ok = run('test_mn2_wallet_explorer_fetch.mjs') && ok;
if (!fetchOnly) ok = run('test_mn2_wallet_explorer_live.mjs') && ok;

process.exit(ok ? 0 : 1);
