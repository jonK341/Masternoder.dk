/**
 * Casino mobile: deep links, install banner, Capacitor hooks, safe-area helpers.
 */
(function () {
    'use strict';

    var TAB_ALIASES = {
        lobby: 'home',
        walk: 'home',
        lounge: 'home',
        games: 'home'
    };

    var STORE = {
        android: 'https://play.google.com/store/apps/details?id=dk.masternoder.casino',
        ios: 'https://apps.apple.com/app/id0000000000'
    };

    function isIos() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent)
            || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function isAndroid() {
        return /Android/i.test(navigator.userAgent);
    }

    function isStandalone() {
        try {
            return window.matchMedia('(display-mode: standalone)').matches
                || window.navigator.standalone === true;
        } catch (e) {
            return false;
        }
    }

    function isCapacitor() {
        return !!(window.Capacitor && window.Capacitor.isNativePlatform && window.Capacitor.isNativePlatform());
    }

    function parseQuery(search) {
        var out = {};
        try {
            new URLSearchParams(search || window.location.search).forEach(function (v, k) {
                out[k] = v;
            });
        } catch (e) { /* optional */ }
        return out;
    }

    function normalizeTab(tab) {
        if (!tab) return null;
        var key = String(tab).toLowerCase();
        return TAB_ALIASES[key] || key;
    }

    /**
     * Resolve deep-link target tab from URL query, hash, or custom scheme path.
     * @returns {string|null}
     */
    function resolveDeepLinkTab(overrides) {
        var q = overrides || parseQuery();
        var game = q.game;
        if (game && document.getElementById('casino-tab-' + game)) {
            return game;
        }
        var tab = normalizeTab(q.tab);
        if (tab && document.getElementById('casino-tab-' + tab)) {
            return tab;
        }
        var hash = (window.location.hash || '').replace(/^#tab-/, '');
        if (hash && document.getElementById('casino-tab-' + hash)) {
            return hash;
        }
        return null;
    }

    function applyDeepLinkFromUrl() {
        var tab = resolveDeepLinkTab();
        if (tab && window.__casinoSwitchTab) {
            window.__casinoSwitchTab(tab);
        }
    }

    function parseCustomSchemeUrl(url) {
        if (!url || typeof url !== 'string') return null;
        try {
            var cleaned = url.replace(/^masternoder:\/\//i, 'https://masternoder.dk/');
            var u = new URL(cleaned);
            return parseQuery(u.search);
        } catch (e) {
            return null;
        }
    }

    function wireCapacitorAppLinks() {
        if (!window.Capacitor || !window.Capacitor.Plugins) return;
        var App = window.Capacitor.Plugins.App;
        if (!App || !App.addListener) return;
        App.addListener('appUrlOpen', function (event) {
            var q = parseCustomSchemeUrl(event && event.url);
            if (!q) return;
            var tab = resolveDeepLinkTab(q);
            if (tab && window.__casinoSwitchTab) {
                window.__casinoSwitchTab(tab);
            }
        });
    }

    function hapticLight() {
        try {
            var Haptics = window.Capacitor && window.Capacitor.Plugins && window.Capacitor.Plugins.Haptics;
            if (Haptics && Haptics.impact) {
                Haptics.impact({ style: 'LIGHT' });
            }
        } catch (e) { /* optional */ }
    }

    function dismissBanner(el) {
        if (!el) return;
        el.classList.add('hidden');
        try { sessionStorage.setItem('casino_install_banner_dismissed', '1'); } catch (e) { /* */ }
    }

    function buildInstallBanner(cfg) {
        if (isStandalone() || isCapacitor()) return;
        try {
            if (sessionStorage.getItem('casino_install_banner_dismissed') === '1') return;
        } catch (e) { /* */ }
        if (cfg && cfg.install_prompt_enabled === false) return;

        var storeUrl = isIos() ? (cfg && cfg.app_store_url) || STORE.ios : (cfg && cfg.play_store_url) || STORE.android;
        if (!storeUrl || storeUrl.indexOf('0000000000') >= 0) {
            if (isIos()) return;
        }

        var bar = document.createElement('div');
        bar.id = 'casino-install-banner';
        bar.className = 'casino-install-banner';
        bar.setAttribute('role', 'region');
        bar.setAttribute('aria-label', 'Get the casino app');
        bar.innerHTML =
            '<div class="casino-install-banner-text">'
            + '<strong>MasterNoder Casino app</strong>'
            + '<span>Faster play, home-screen shortcut, deep links to your favorite games.</span>'
            + '</div>'
            + '<div class="casino-install-banner-actions">'
            + '<a class="casino-install-banner-cta" href="' + storeUrl + '" rel="noopener">Get app</a>'
            + '<button type="button" class="casino-install-banner-dismiss" aria-label="Dismiss">✕</button>'
            + '</div>';

        bar.querySelector('.casino-install-banner-dismiss').addEventListener('click', function () {
            dismissBanner(bar);
        });

        var host = document.querySelector('.casino-page');
        if (host) {
            host.insertBefore(bar, host.firstChild);
        }
    }

    function loadMobileConfig() {
        return fetch('/api/casino/mobile/config', { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .catch(function () { return {}; });
    }

    function boot() {
        document.documentElement.classList.add('casino-mobile-ready');
        if (isCapacitor()) {
            document.body.classList.add('casino-capacitor-native');
        }
        if (isIos()) {
            document.body.classList.add('casino-mobile-ios');
        }
        if (isAndroid()) {
            document.body.classList.add('casino-mobile-android');
        }

        wireCapacitorAppLinks();

        loadMobileConfig().then(function (cfg) {
            if (cfg && cfg.success) {
                if (cfg.play_store_url) STORE.android = cfg.play_store_url;
                if (cfg.app_store_url) STORE.ios = cfg.app_store_url;
            }
            buildInstallBanner(cfg);
        });

        window.addEventListener('casino:ready', function () {
            applyDeepLinkFromUrl();
        });

        if (window.__casinoSwitchTab) {
            applyDeepLinkFromUrl();
        }
    }

    window.__casinoMobile = {
        resolveDeepLinkTab: resolveDeepLinkTab,
        applyDeepLinkFromUrl: applyDeepLinkFromUrl,
        hapticLight: hapticLight,
        isCapacitor: isCapacitor,
        isStandalone: isStandalone,
        TAB_ALIASES: TAB_ALIASES
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
