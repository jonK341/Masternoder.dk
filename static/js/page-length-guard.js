/**
 * Page length guard — caps tall content to ~3 viewport heights (per region).
 * Loaded from navigation-toolbar.js on all toolbar pages.
 */
(function () {
    'use strict';

    var MAX_VIEWPORTS = 3;
    var NAV_OFFSET = 72;
    var TOLERANCE_PX = 32;

    var CAP_SELECTORS = [
        '.game-tab-content.active',
        '.casino-v10-panel:not(.hidden)',
        '.casino-v12-panel:not(.hidden)',
        '.casino-v13-panel:not(.hidden)',
        '.casino-v14-multiplay:not(.hidden)',
        '.casino-grid',
        '.tab-panel.active',
        '.tab-content.active',
        '.page-panel.active',
        '[role="tabpanel"]:not([hidden])',
        '.profile-tab-panel.active',
        '.shop-tab-panel.active',
        '.lab-hub-panel:not(.hidden)',
        '.page-main',
        '.page-main-wrap',
        '[data-page-layout="standard"]',
        '.shop-page',
        '.lab-page',
        '.hosting-page',
        '.explorer-page',
        '.profile-page',
        '.profile-container',
        '.aggregator-page',
        '.agg-main-wrap',
        '.chat-page',
        '.discord-play-body .dp-main',
        'main#mainContent',
        'main.fp-main',
    ];

    function hasTabbedChild(el) {
        if (!el || !el.querySelector) return false;
        return !!el.querySelector(
            '.casino-v10-panel, .game-tab-content, .tab-panel, .tab-content, .page-panel, [role="tabpanel"]'
        );
    }

    function debounce(fn, ms) {
        var t;
        return function () {
            clearTimeout(t);
            var args = arguments;
            var ctx = this;
            t = setTimeout(function () { fn.apply(ctx, args); }, ms);
        };
    }

    function loadCapCss() {
        if (document.querySelector('link[href*="page-length-cap"]')) return;
        var link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/css/page-length-cap.css?v=20260624';
        document.head.appendChild(link);
    }

    function ensureLayoutStandard() {
        if (!document.querySelector('link[href*="page-layout-metrics"]')) return;
        if (!document.body.classList.contains('layout-standard')) {
            document.body.classList.add('layout-standard');
        }
    }

    function maxScrollPx() {
        var vh = window.innerHeight || document.documentElement.clientHeight || 800;
        return Math.max(280, Math.floor(vh * MAX_VIEWPORTS - NAV_OFFSET));
    }

    function isExempt() {
        if (document.body && document.body.getAttribute('data-page-length') === 'unlimited') {
            return true;
        }
        return false;
    }

    function addHint(el) {
        if (!el || el.querySelector(':scope > .page-length-hint')) return;
        var hint = document.createElement('div');
        hint.className = 'page-length-hint';
        hint.setAttribute('role', 'status');
        hint.textContent = 'Scroll this section (max 3 screens) — use tabs above for more content';
        el.insertAdjacentElement('afterbegin', hint);
    }

    function capElement(el) {
        if (!el || el.getAttribute('data-page-length') === 'unlimited') return false;
        if (el.classList.contains('page-length-capped')) {
            el.style.setProperty('--page-scroll-max-height', maxScrollPx() + 'px');
            return true;
        }
        if (hasTabbedChild(el)) return false;
        var maxH = maxScrollPx();
        if (el.scrollHeight <= maxH + TOLERANCE_PX) return false;
        el.classList.add('page-length-capped');
        el.style.setProperty('--page-scroll-max-height', maxH + 'px');
        addHint(el);
        return true;
    }

    function lockRootIfNeeded(didCap) {
        if (!didCap) {
            document.documentElement.classList.remove('page-length-root-locked');
            return;
        }
        var docH = document.documentElement.scrollHeight;
        var viewH = window.innerHeight || 800;
        if (docH > viewH + TOLERANCE_PX) {
            document.documentElement.classList.add('page-length-root-locked');
        }
    }

    function scan() {
        if (isExempt()) return;
        var seen = new Set();
        var anyCapped = false;

        CAP_SELECTORS.forEach(function (sel) {
            try {
                document.querySelectorAll(sel).forEach(function (el) {
                    if (seen.has(el)) return;
                    seen.add(el);
                    if (capElement(el)) anyCapped = true;
                });
            } catch (e) { /* invalid selector in old browsers */ }
        });

        var docMax = maxScrollPx() + NAV_OFFSET;
        if (document.documentElement.scrollHeight > docMax + viewTolerance()) {
            var fallback = document.querySelector('main')
                || document.querySelector('.page-container')
                || document.querySelector('.page-shell')
                || document.body;
            if (fallback && !seen.has(fallback) && capElement(fallback)) {
                anyCapped = true;
            }
        }

        lockRootIfNeeded(anyCapped);
    }

    function viewTolerance() {
        return (window.innerHeight || 800) * 0.15;
    }

    function bindTabRescan() {
        document.addEventListener('click', function (ev) {
            var t = ev.target;
            if (!t || !t.closest) return;
            if (t.closest(
                '[role="tab"], .tab-btn, .tab-button, .page-tab, .game-tab, '
                + '.casino-v10-main-tab, .profile-tab, .shop-tab, .lab-hub-tab'
            )) {
                setTimeout(scan, 60);
                setTimeout(scan, 400);
            }
        });
    }

    function init() {
        loadCapCss();
        ensureLayoutStandard();
        scan();
        bindTabRescan();
        window.addEventListener('resize', debounce(scan, 180));
        window.addEventListener('load', function () { setTimeout(scan, 200); });
        if (typeof MutationObserver !== 'undefined' && document.body) {
            var mo = new MutationObserver(debounce(scan, 120));
            mo.observe(document.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['class', 'hidden', 'style'],
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { setTimeout(init, 50); });
    } else {
        setTimeout(init, 50);
    }
})();
