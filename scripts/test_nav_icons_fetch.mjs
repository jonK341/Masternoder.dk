/**
 * Live smoke test (fetch-only): navigation toolbar assets on masternoder.dk
 */
const BASE = process.env.NAV_TEST_BASE || 'https://masternoder.dk';

const assetUrls = [
  '/static/js/navigation-toolbar.js',
  '/static/css/navigation-toolbar.css',
  '/static/img/nav/brand.svg',
  '/static/img/nav/home.svg',
  '/static/img/nav/trophy.svg',
  '/static/img/nav/game.svg',
  '/static/img/nav/battlegrounds.svg',
  '/static/img/agents/battle_strategy_agent.svg',
  '/static/img/agents/content_generator_agent.svg',
];

const pages = ['/', '/game', '/battle', '/generator'];

function ok(label, pass, detail = '') {
  const mark = pass ? 'PASS' : 'FAIL';
  console.log(`[${mark}] ${label}${detail ? ` — ${detail}` : ''}`);
  return pass;
}

async function get(path) {
  const res = await fetch(BASE + path, { redirect: 'follow' });
  const text = res.ok ? await res.text() : '';
  return { res, text };
}

let allPass = true;

for (const p of assetUrls) {
  const { res, text } = await get(p);
  allPass = ok(`GET ${p}`, res.ok, String(res.status)) && allPass;
  if (p.endsWith('.js') && res.ok) {
    allPass = ok('JS NAV_ICON_IMAGES map', text.includes('NAV_ICON_IMAGES')) && allPass;
    allPass = ok('JS _renderIcon helper', text.includes('_renderIcon')) && allPass;
    allPass = ok('JS battle icon path', text.includes('/static/img/agents/battle_strategy_agent.svg')) && allPass;
    allPass = ok('JS brand icon path', text.includes('/static/img/nav/brand.svg')) && allPass;
  }
  if (p.endsWith('.css') && res.ok) {
    allPass = ok('CSS nav-toolbar-link-img', text.includes('nav-toolbar-link-img')) && allPass;
    allPass = ok('CSS navIconPulse animation', text.includes('navIconPulse')) && allPass;
  }
  if (p.endsWith('.svg') && res.ok) {
    allPass = ok(`SVG ${p} content`, text.trimStart().startsWith('<svg')) && allPass;
  }
}

for (const p of pages) {
  const { res, text } = await get(p);
  allPass = ok(`GET ${p}`, res.ok, String(res.status)) && allPass;
  if (res.ok) {
    const hasNavJs = /navigation-toolbar\.js/.test(text);
    const hasNavCss = /navigation-toolbar\.css/.test(text);
    allPass = ok(`${p} loads navigation-toolbar.js`, hasNavJs) && allPass;
    allPass = ok(`${p} loads navigation-toolbar.css`, hasNavCss) && allPass;
  }
}

const { res: homeRes, text: homeHtml } = await get('/');
if (homeRes.ok) {
  const vMatch = homeHtml.match(/navigation-toolbar\.js\?v=([^"']+)/);
  allPass = ok('Homepage cache-bust version present', !!vMatch, vMatch?.[1] || '') && allPass;
}

console.log(allPass ? '\nAll fetch-based nav icon tests passed.' : '\nSome fetch-based tests failed.');
process.exit(allPass ? 0 : 1);
