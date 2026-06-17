/**
 * Fast MN2 wallet + explorer smoke (fetch/API). No browser required.
 * Usage: node scripts/test_mn2_wallet_explorer_fetch.mjs
 *   MN2_TEST_BASE=https://masternoder.dk MN2_TEST_USER=default_user node scripts/...
 */
const BASE = (process.env.MN2_TEST_BASE || process.env.NAV_TEST_BASE || 'https://masternoder.dk').replace(/\/$/, '');
const USER = process.env.MN2_TEST_USER || process.env.USER_ID || 'default_user';

function ok(label, pass, detail = '') {
  const mark = pass ? 'PASS' : 'FAIL';
  console.log(`[${mark}] ${label}${detail ? ` — ${detail}` : ''}`);
  return pass;
}

async function getJson(path) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'application/json' },
    redirect: 'follow',
  });
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  return { res, data };
}

async function getHtml(path) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'text/html', 'User-Agent': 'mn2-smoke-fetch/1' },
    redirect: 'follow',
  });
  const text = res.ok ? await res.text() : '';
  return { res, text };
}

let allPass = true;
const enc = encodeURIComponent(USER);

console.log(`MN2 fetch smoke — ${BASE} user=${USER}\n`);

// --- Wallet APIs ---
{
  const { res, data } = await getJson(`/api/mn2/balance?user_id=${enc}`);
  allPass = ok('GET /api/mn2/balance', res.ok && data?.success, `HTTP ${res.status}`) && allPass;
  allPass = ok('balance has mn2_balance number', data?.success && typeof data.mn2_balance === 'number', String(data?.mn2_balance)) && allPass;
}

{
  const { res, data } = await getJson(`/api/mn2/deposit-address?user_id=${enc}`);
  allPass = ok('GET /api/mn2/deposit-address', res.ok && data?.success, `HTTP ${res.status}`) && allPass;
  const addr = (data?.deposit_address || '').trim();
  if (addr) {
    allPass = ok('deposit address present', addr.length >= 20, addr.slice(0, 12) + '…') && allPass;
  } else {
    allPass = ok('deposit address optional (pool may be empty)', true, data?.error || 'no address yet') && allPass;
  }
}

{
  const { res, data } = await getJson(`/api/mn2/transactions?user_id=${enc}&limit=5`);
  allPass = ok('GET /api/mn2/transactions', res.ok && data?.success, `HTTP ${res.status} n=${(data?.transactions || []).length}`) && allPass;
}

{
  const { res, data } = await getJson(`/api/mn2/wallet-activity?user_id=${enc}&days=5`);
  allPass = ok('GET /api/mn2/wallet-activity', res.ok && data?.success !== false, `HTTP ${res.status}`) && allPass;
}

{
  const { res, data } = await getJson('/api/mn2/price');
  allPass = ok('GET /api/mn2/price', res.ok && data?.success, `HTTP ${res.status} usd=${data?.mn2_usd_price}`) && allPass;
}

// --- Explorer APIs ---
{
  const { res, data } = await getJson('/api/mn2/network-overview');
  allPass = ok('GET /api/mn2/network-overview', res.ok && data?.success, `HTTP ${res.status}`) && allPass;
  const hasHeight = data?.block_height != null && !Number.isNaN(Number(data.block_height));
  const hasPrice = data?.mn2_usd_price != null && !Number.isNaN(Number(data.mn2_usd_price));
  allPass = ok('network-overview block_height', hasHeight, String(data?.block_height)) && allPass;
  allPass = ok('network-overview price or fallback', hasPrice || data?.success, hasPrice ? `$${data.mn2_usd_price}` : 'price null (Chainz?)') && allPass;
}

{
  const { res, data } = await getJson('/api/mn2/recent-blocks?limit=5');
  allPass = ok('GET /api/mn2/recent-blocks', res.ok && data?.success !== false, `HTTP ${res.status} blocks=${(data?.blocks || []).length}`) && allPass;
}

{
  const { res, data } = await getJson('/api/mn2/masternodes?limit=5');
  allPass = ok('GET /api/mn2/masternodes', res.ok && data?.success !== false, `HTTP ${res.status}`) && allPass;
}

{
  const { res, data } = await getJson('/api/mn2/network-history?hours=24&limit=10');
  allPass = ok('GET /api/mn2/network-history', res.ok && data?.success !== false, `HTTP ${res.status}`) && allPass;
}

// --- HTML shells ---
{
  const { res, text } = await getHtml('/profile?tab=wallet');
  const hasWallet = text.includes('profile-mn2-wallet-card') && text.includes('profile-mn2-balance');
  allPass = ok('GET /profile?tab=wallet HTML', res.ok && hasWallet, `HTTP ${res.status}`) && allPass;
}

{
  const { res, text } = await getHtml('/explorer');
  const hasExplorer = text.includes('t-height') && text.includes('mn2-explorer-overview.js');
  allPass = ok('GET /explorer HTML', res.ok && hasExplorer, `HTTP ${res.status}`) && allPass;
}

console.log(allPass ? '\nAll MN2 wallet/explorer fetch tests passed.' : '\nSome MN2 fetch tests failed.');
process.exit(allPass ? 0 : 1);
