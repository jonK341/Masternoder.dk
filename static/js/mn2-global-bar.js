/**
 * Compact MN2 bar for pages without a full mn2-page-strip.
 */
(function (global) {
    'use strict';

    function fmt(n) {
        return global.Mn2SiteBridge ? global.Mn2SiteBridge.fmtMn2(n) : String(n);
    }

    function inject() {
        if (global.document.querySelector('.mn2-page-strip')) return;
        if (global.document.getElementById('mn2-global-bar')) return;

        var bar = global.document.createElement('div');
        bar.id = 'mn2-global-bar';
        bar.className = 'mn2-global-bar';
        bar.innerHTML =
            '<span class="mn2-global-label">MN2</span>' +
            '<strong id="mn2-global-balance">—</strong>' +
            '<span id="mn2-global-rate" class="mn2-global-rate"></span>' +
            '<a href="/market">Market</a>' +
            '<a href="/profile#mn2-wallet">Wallet</a>';
        bar.style.cssText = 'display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:8px 16px 0;padding:8px 14px;border-radius:999px;border:1px solid rgba(0,212,255,0.25);background:rgba(0,20,30,0.55);font-size:0.82rem;position:relative;z-index:50;';
        bar.querySelectorAll('a').forEach(function (a) {
            a.style.cssText = 'color:#00d4ff;text-decoration:none;font-weight:700;';
        });
        var nav = global.document.querySelector('.nav-toolbar, .page-nav, nav.page-nav, header');
        if (nav && nav.parentNode) {
            nav.parentNode.insertBefore(bar, nav.nextSibling);
        } else {
            global.document.body.insertBefore(bar, global.document.body.firstChild);
        }

        if (!global.Mn2SiteBridge) return;
        global.Mn2SiteBridge.loadBalance().then(function (d) {
            var bal = (d && (d.balance != null ? d.balance : d.mn2_balance)) || 0;
            var el = global.document.getElementById('mn2-global-balance');
            if (el) el.textContent = fmt(bal);
        }).catch(function () {});
        global.Mn2SiteBridge.loadPrice().then(function (d) {
            var p = d && (d.price_usd != null ? d.price_usd : d.usd);
            var el = global.document.getElementById('mn2-global-rate');
            if (el && p != null) el.textContent = '$' + Number(p).toFixed(4);
        }).catch(function () {});
    }

    function loadScripts(cb) {
        if (global.Mn2SiteBridge) { cb(); return; }
        var s = global.document.createElement('script');
        s.src = '/static/js/mn2-site-bridge.js?v=20260614d';
        s.onload = cb;
        global.document.head.appendChild(s);
    }

    global.document.addEventListener('DOMContentLoaded', function () {
        loadScripts(inject);
    });
})(window);
