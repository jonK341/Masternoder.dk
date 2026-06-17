/**
 * Live smoke test: navigation toolbar image icons on masternoder.dk
 */
import { chromium } from 'playwright';

const BASE = process.env.NAV_TEST_BASE || 'https://masternoder.dk';
const paths = [
  '/',
  '/game',
  '/battle',
];

const assetUrls = [
  '/static/js/navigation-toolbar.js',
  '/static/css/navigation-toolbar.css',
  '/static/img/nav/brand.svg',
  '/static/img/nav/home.svg',
  '/static/img/agents/battle_strategy_agent.svg',
];

function ok(label, pass, detail = '') {
  const mark = pass ? 'PASS' : 'FAIL';
  console.log(`[${mark}] ${label}${detail ? ` — ${detail}` : ''}`);
  return pass;
}

async function checkAssets(page) {
  let all = true;
  for (const p of assetUrls) {
    const url = BASE + p;
    const res = await page.request.get(url);
    const pass = res.ok();
    all = ok(`asset ${p}`, pass, String(res.status())) && all;
    if (p.endsWith('.js') && pass) {
      const body = await res.text();
      all = ok('JS has NAV_ICON_IMAGES', body.includes('NAV_ICON_IMAGES')) && all;
      all = ok('JS has _renderIcon', body.includes('_renderIcon')) && all;
    }
    if (p.endsWith('.css') && pass) {
      const body = await res.text();
      all = ok('CSS has nav-toolbar-link-img', body.includes('nav-toolbar-link-img')) && all;
    }
  }
  return all;
}

async function checkPage(page, path) {
  const url = BASE + path;
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
  await page.waitForSelector('#navToolbar', { timeout: 15000 });

  const toolbar = page.locator('#navToolbar');
  const imgCount = await toolbar.locator('.nav-toolbar-link-img').count();
  const brandImg = await toolbar.locator('.nav-toolbar-brand .nav-toolbar-link-img').count();
  const portalTrigger = await toolbar.locator('#navPortalTrigger').count();

  let pass = true;
  pass = ok(`${path} toolbar present`, await toolbar.count() === 1) && pass;
  pass = ok(`${path} image icons rendered`, imgCount >= 1, `count=${imgCount}`) && pass;
  pass = ok(`${path} brand icon img`, brandImg >= 1) && pass;

  if (portalTrigger > 0) {
    await page.locator('#navPortalTrigger').click();
    await page.waitForSelector('#navPortalPanel.open', { timeout: 5000 });
    const gridImgs = await page.locator('#navPortalGrid .nav-toolbar-link-img').count();
    pass = ok(`${path} portal grid icons`, gridImgs >= 10, `count=${gridImgs}`) && pass;
  }

  // Wait for icon images to finish loading (portal opens many at once)
  await page.waitForFunction(() => {
    const imgs = [...document.querySelectorAll('#navToolbar .nav-toolbar-link-img')];
    return imgs.length > 0 && imgs.every((img) => img.complete && img.naturalWidth > 0);
  }, { timeout: 15000 }).catch(() => {});

  // Sample broken-image check: img visible and naturalWidth > 0
  const broken = await page.evaluate(() => {
    const imgs = [...document.querySelectorAll('#navToolbar .nav-toolbar-link-img')];
    return imgs.filter((img) => !img.complete || img.naturalWidth === 0).map((img) => img.src);
  });
  pass = ok(`${path} no broken nav images`, broken.length === 0, broken.slice(0, 3).join(', ')) && pass;

  return pass;
}

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
let allPass = true;

try {
  allPass = (await checkAssets(page)) && allPass;
  for (const p of paths) {
    allPass = (await checkPage(page, p)) && allPass;
  }
} finally {
  await browser.close();
}

console.log(allPass ? '\nAll navigation icon tests passed.' : '\nSome tests failed.');
process.exit(allPass ? 0 : 1);
