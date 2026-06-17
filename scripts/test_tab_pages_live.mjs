/**
 * Live smoke test for profile/casino/lab/monetization tab UIs.
 * Usage: node scripts/test_tab_pages_live.mjs
 */
import { chromium } from 'playwright';

const BASE = 'https://masternoder.dk';

const CASES = [
  {
    name: 'Profile',
    url: `${BASE}/profile`,
    nav: '#profile-hub-nav',
    tabBtn: '.profile-hub-tab[data-hub-scroll="wallet"]',
    panelVisible: '#profile-mn2-wallet-card:not([hidden])',
    panelHidden: '#profile-section-shop[hidden]',
    urlTab: 'wallet',
  },
  {
    name: 'Casino',
    url: `${BASE}/casino/`,
    nav: '#casino-games-nav',
    tabBtn: '.casino-game-tab[data-game="plinko"]',
    panelVisible: '.casino-card.casino-game-active[data-casino-game="plinko"]',
    panelHidden: '.casino-card[data-casino-game="crash"]:not(.casino-game-active)',
    urlTab: 'game=plinko',
  },
  {
    name: 'Lab',
    url: `${BASE}/lab`,
    nav: '#lab-hub-nav',
    tabBtn: '.lab-hub-tab[data-lab-tab="chapter"]',
    panelVisible: '#lab-chapter-2:not([hidden])',
    panelHidden: '#lab-documentation[hidden]',
    urlTab: 'tab=chapter',
  },
  {
    name: 'Monetization',
    url: `${BASE}/monetization`,
    nav: '#mon-hub-nav',
    tabBtn: '.mon-hub-tab[data-mon-tab="streams"]',
    panelVisible: '[data-mon-tab="streams"]:not([hidden])',
    panelHidden: '[data-mon-tab="mn2"][hidden]',
    urlTab: 'tab=streams',
  },
];

async function waitForProfileContent(page) {
  await page.waitForSelector('#profile-hub-nav', { timeout: 45000 });
  // Profile hides content until load completes
  await page.waitForFunction(() => {
    const block = document.getElementById('profile-content-block');
    return block && block.style.display !== 'none';
  }, { timeout: 45000 }).catch(() => {});
}

async function runCase(page, c) {
  const results = [];
  const fail = (msg) => results.push({ ok: false, msg });
  const pass = (msg) => results.push({ ok: true, msg });

  await page.goto(c.url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  if (c.name === 'Profile') await waitForProfileContent(page);

  const nav = page.locator(c.nav);
  if (!(await nav.count())) return fail(`Missing nav ${c.nav}`);
  pass(`Nav present: ${c.nav}`);

  const tabs = await page.locator(`${c.nav} button`).count();
  if (tabs < 2) return fail(`Expected multiple tabs, got ${tabs}`);
  pass(`${tabs} tab buttons`);

  await page.locator(c.tabBtn).click();
  await page.waitForTimeout(400);

  if (!(await page.locator(c.panelVisible).count())) {
    return fail(`Active panel not visible after click: ${c.panelVisible}`);
  }
  pass('Target panel visible after tab click');

  if (!(await page.locator(c.panelHidden).count())) {
    return fail(`Other panel should be hidden: ${c.panelHidden}`);
  }
  pass('Other panel hidden');

  const href = page.url();
  if (!href.includes(c.urlTab)) {
    return fail(`URL missing ${c.urlTab} (got ${href})`);
  }
  pass(`URL updated (${c.urlTab})`);

  return { ok: true, results };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const summary = [];

  for (const c of CASES) {
    process.stdout.write(`\n=== ${c.name} ===\n`);
    try {
      const out = await runCase(page, c);
      if (out.ok === false) {
        summary.push({ page: c.name, ok: false, error: out.msg });
        console.log('FAIL:', out.msg);
        continue;
      }
      for (const r of out.results) {
        console.log(r.ok ? '  OK' : '  FAIL', r.msg);
      }
      summary.push({ page: c.name, ok: out.results.every((r) => r.ok) });
    } catch (e) {
      summary.push({ page: c.name, ok: false, error: String(e.message || e) });
      console.log('ERROR:', e.message || e);
    }
  }

  await browser.close();

  console.log('\n=== SUMMARY ===');
  for (const s of summary) {
    console.log(`${s.ok ? 'PASS' : 'FAIL'} ${s.page}${s.error ? ' — ' + s.error : ''}`);
  }
  process.exit(summary.every((s) => s.ok) ? 0 : 1);
}

main();
