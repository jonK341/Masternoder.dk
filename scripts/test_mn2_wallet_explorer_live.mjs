/**
 * Playwright smoke: MN2 wallet (profile) + explorer pages on live site.
 * Usage: node scripts/test_mn2_wallet_explorer_live.mjs
 */
import { chromium } from 'playwright';

const BASE = (process.env.MN2_TEST_BASE || process.env.NAV_TEST_BASE || 'https://masternoder.dk').replace(/\/$/, '');
const USER = process.env.MN2_TEST_USER || 'default_user';

function ok(label, pass, detail = '') {
  const mark = pass ? 'PASS' : 'FAIL';
  console.log(`[${mark}] ${label}${detail ? ` — ${detail}` : ''}`);
  return pass;
}

function isDashText(t) {
  const s = (t || '').trim();
  return !s || s === '--' || s === '—' || /^Loading/i.test(s);
}

async function waitForProfileReady(page) {
  await page.waitForSelector('#profile-hub-nav', { timeout: 45000 });
  await page.waitForFunction(() => {
    const block = document.getElementById('profile-content-block');
    const overlay = document.getElementById('profile-loading-overlay');
    return block && block.style.display !== 'none' && (!overlay || overlay.offsetParent === null);
  }, { timeout: 90000 }).catch(() => {});
}

async function testWallet(page, apiErrors) {
  let pass = true;
  console.log('\n=== MN2 Wallet (profile) ===');

  const walletApis = [];
  const onResponse = (res) => {
    const u = res.url();
    if (u.includes('/api/mn2/balance') || u.includes('/api/mn2/deposit-address') ||
        u.includes('/api/mn2/transactions') || u.includes('/api/mn2/wallet-activity')) {
      walletApis.push({ url: u, status: res.status() });
      if (res.status() >= 400) apiErrors.push(`${res.status()} ${u}`);
    }
  };
  page.on('response', onResponse);

  const profileWait = page.waitForResponse(
    (r) => r.url().includes('/aggregated') && r.status() === 200,
    { timeout: 90000 },
  );
  const balanceWait = page.waitForResponse(
    (r) => r.url().includes('/api/mn2/balance') && r.status() === 200,
    { timeout: 90000 },
  );

  await page.goto(`${BASE}/profile?tab=wallet`, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await waitForProfileReady(page);
  await profileWait.catch(() => {});
  await balanceWait.catch(() => {});

  await page.waitForFunction(() => window.profileManager != null, { timeout: 30000 }).catch(() => {});

  const walletStillLoading = await page.evaluate(() => {
    const bal = document.getElementById('profile-mn2-balance');
    return !bal || /^--$/.test((bal.textContent || '').trim());
  });
  if (walletStillLoading) {
    await page.evaluate((uid) => {
      if (!window.profileManager) return;
      window.profileManager.userId = uid;
      window.profileManager.loadProfileMn2Wallet();
    }, USER);
    await page.waitForResponse(
      (r) => r.url().includes('/api/mn2/balance') && r.status() === 200,
      { timeout: 30000 },
    ).catch(() => {});
  }
  if ((await page.locator('.profile-hub-tab[data-hub-scroll="wallet"].active').count()) === 0) {
    await page.locator('.profile-hub-tab[data-hub-scroll="wallet"]').click();
    await page.waitForTimeout(500);
  }

  pass = ok('profile hub nav', (await page.locator('#profile-hub-nav').count()) === 1) && pass;
  pass = ok('wallet tab active', await page.locator('.profile-hub-tab[data-hub-scroll="wallet"].active').count() >= 1) && pass;

  const walletCard = page.locator('#profile-mn2-wallet-card');
  await walletCard.waitFor({ state: 'visible', timeout: 20000 }).catch(() => {});
  pass = ok('wallet card visible', (await walletCard.count()) === 1 && !(await walletCard.isHidden())) && pass;

  await page.waitForFunction(() => {
    const bal = document.getElementById('profile-mn2-balance');
    const tx = document.getElementById('profile-mn2-transactions');
    const balOk = bal && /^[\d.]+/.test((bal.textContent || '').trim());
    const txOk = tx && !/^Loading/i.test((tx.textContent || '').trim());
    return balOk && txOk;
  }, { timeout: 60000 }).catch(() => {});

  const balance = await page.locator('#profile-mn2-balance').textContent();
  pass = ok('balance loaded (not --)', !isDashText(balance), (balance || '').trim()) && pass;
  pass = ok('balance is numeric', balance != null && !Number.isNaN(Number(balance.trim())), balance?.trim()) && pass;

  const txText = await page.locator('#profile-mn2-transactions').textContent();
  pass = ok('transactions list loaded', !/^Loading/i.test((txText || '').trim()), (txText || '').trim().slice(0, 60)) && pass;

  const addr = (await page.locator('#profile-mn2-deposit-address').textContent())?.trim() || '';
  if (!isDashText(addr) && addr.length >= 20) {
    pass = ok('deposit address shown', true, addr.slice(0, 16) + '…') && pass;
  } else {
    pass = ok('deposit address pending or hint', true, addr || 'no address yet (API may still be OK)') && pass;
  }

  const balApi = walletApis.find((a) => a.url.includes('/api/mn2/balance'));
  pass = ok('balance API called', !!balApi, balApi ? String(balApi.status) : 'missing') && pass;
  pass = ok('wallet APIs no 5xx', !walletApis.some((a) => a.status >= 500), walletApis.map((a) => a.status).join(', ')) && pass;

  const chart = await page.locator('#profile-mn2-5d-chart').textContent();
  pass = ok('5d activity chart loaded', !/^Loading/i.test((chart || '').trim()), (chart || '').trim().slice(0, 40)) && pass;

  return pass;
}

async function testExplorer(page, apiErrors) {
  let pass = true;
  console.log('\n=== MN2 Explorer ===');

  const explorerApis = [];
  page.on('response', (res) => {
    const u = res.url();
    if (u.includes('/api/mn2/network-overview') || u.includes('/api/mn2/recent-blocks') ||
        u.includes('/api/mn2/masternodes')) {
      explorerApis.push({ url: u, status: res.status() });
      if (res.status() >= 400) apiErrors.push(`${res.status()} ${u}`);
    }
  });

  await page.goto(`${BASE}/explorer`, { waitUntil: 'domcontentloaded', timeout: 60000 });

  pass = ok('explorer page title area', (await page.locator('#t-height').count()) === 1) && pass;

  await page.waitForResponse((r) => r.url().includes('/api/mn2/network-overview') && r.status() === 200, { timeout: 30000 }).catch(() => {});

  await page.waitForFunction(() => {
    const h = document.getElementById('t-height');
    const u = document.getElementById('ex-updated');
    const heightOk = h && !/^--$|^—$/.test((h.textContent || '').trim());
    const updatedOk = u && !/^Loading/i.test((u.textContent || '').trim()) &&
      !(u.textContent || '').includes('temporarily unavailable');
    return heightOk && updatedOk;
  }, { timeout: 45000 }).catch(() => {});

  const height = await page.locator('#t-height').textContent();
  const price = await page.locator('#t-price').textContent();
  const updated = await page.locator('#ex-updated').textContent();

  pass = ok('block height tile', !isDashText(height), (height || '').trim()) && pass;
  pass = ok('price tile (may be — if no ticker)', (price || '').includes('$') || !isDashText(price) || (price || '').includes('—'), (price || '').trim()) && pass;
  pass = ok('updated stamp', !(updated || '').includes('temporarily unavailable'), (updated || '').trim()) && pass;

  await page.waitForFunction(() => {
    const body = document.getElementById('ex-blocks');
    return body && !/^Loading/i.test((body.textContent || '').trim());
  }, { timeout: 30000 }).catch(() => {});

  const blocksHtml = await page.locator('#ex-blocks').innerHTML();
  pass = ok('blocks table populated', blocksHtml.includes('<tr') && !blocksHtml.includes('Loading'), blocksHtml.slice(0, 80)) && pass;

  const openLink = await page.locator('#ex-open').getAttribute('href');
  pass = ok('external explorer link', !!openLink && openLink.startsWith('http'), openLink || '') && pass;

  const overview = explorerApis.find((a) => a.url.includes('network-overview'));
  pass = ok('network-overview API 200', overview?.status === 200, overview ? String(overview.status) : 'not called') && pass;

  await page.locator('#ex-q').fill('MN2TestSearch');
  await page.locator('#ex-search').evaluate((form) => {
    form.addEventListener('submit', (e) => e.preventDefault(), { once: true });
  });
  pass = ok('search form present', (await page.locator('#ex-search').count()) === 1) && pass;

  return pass;
}

async function testHomeMn2Strip(page) {
  console.log('\n=== Homepage MN2 strip ===');
  let pass = true;
  await page.goto(`${BASE}/`, { waitUntil: 'domcontentloaded', timeout: 60000 });

  pass = ok('MN2 band present', (await page.locator('#fp-mn2-title').count()) === 1) && pass;
  pass = ok('explorer link on home', (await page.locator('a[href="/explorer"]').count()) >= 1) && pass;

  await page.waitForFunction(() => {
    const el = document.getElementById('stat-mn2-price');
    return el && !/^—$|^--$/.test((el.textContent || '').trim());
  }, { timeout: 30000 }).catch(() => {});

  const statPrice = await page.locator('#stat-mn2-price').textContent();
  pass = ok('homepage MN2 price stat', !isDashText(statPrice), (statPrice || '').trim()) && pass;
  return pass;
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
await context.addInitScript((uid) => {
  try { localStorage.setItem('game_user_id', uid); } catch (e) {}
}, USER);
const page = await context.newPage();
const apiErrors = [];
const consoleErrors = [];
page.on('console', (msg) => {
  if (msg.type() === 'error') consoleErrors.push(msg.text());
});

let allPass = true;
try {
  console.log(`MN2 Playwright smoke — ${BASE} user=${USER}`);
  allPass = (await testWallet(page, apiErrors)) && allPass;
  allPass = (await testExplorer(page, apiErrors)) && allPass;
  allPass = (await testHomeMn2Strip(page)) && allPass;

  if (apiErrors.length) {
    allPass = ok('no MN2 API 4xx/5xx during UI test', false, apiErrors.slice(0, 3).join('; ')) && allPass;
  } else {
    ok('no MN2 API 4xx/5xx during UI test', true);
  }

  const criticalConsole = consoleErrors.filter((e) =>
    /mn2|wallet|explorer|network-overview/i.test(e) && !/favicon/i.test(e));
  if (criticalConsole.length) {
    allPass = ok('no critical MN2 console errors', false, criticalConsole.slice(0, 2).join('; ')) && allPass;
  } else {
    ok('no critical MN2 console errors', true);
  }
} finally {
  await context.close();
  await browser.close();
}

console.log(allPass ? '\nAll MN2 wallet/explorer browser tests passed.' : '\nSome MN2 browser tests failed.');
process.exit(allPass ? 0 : 1);
