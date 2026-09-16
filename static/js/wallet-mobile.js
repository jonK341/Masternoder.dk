/**
 * MN2 Wallet mobile: deep links, PWA install hints, Capacitor hooks, safe-area helpers.
 */
(function () {
    'use strict';

    var RELEASE_TAG = 'wallet-mobile-v0.1.0-preview';
    var RELEASE_APK_NAME = 'MasterNoder-Wallet-android-v0.1.0-preview.apk';
    var DOWNLOAD_DOC_PATH = 'docs/WALLET_DOWNLOAD.md';

    function parseQuery(search) {
        var out = {};
        try {
            new URLSearchParams(search || window.location.search).forEach(function (v, k) {
                out[k] = v;
            });
        } catch (e) { /* optional */ }
        return out;
    }

    function isWalletPage() {
        return /^\/wallets(\/|$)/.test(window.location.pathname || '');
    }

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

    function appShellMode() {
        var q = parseQuery();
        var app = q.app || '';
        if (app === 'wallet-twa' || app === 'wallet-capacitor' || app === 'wallet-pwa') {
            return app;
        }
        if (isCapacitor()) return 'wallet-capacitor';
        if (isStandalone()) return 'wallet-pwa';
        return null;
    }

    function applyShellClass() {
        var mode = appShellMode();
        if (!mode) return;
        document.documentElement.classList.add('wallet-mobile-active', 'wallet-mobile-' + mode.replace(/-/g, '_'));
    }

    function injectManifest() {
        if (document.querySelector('link[rel="manifest"][href="/wallets/manifest.webmanifest"]')) return;
        var head = document.head || document.getElementsByTagName('head')[0];
        if (!head) return;
        var link = document.createElement('link');
        link.rel = 'manifest';
        link.href = '/wallets/manifest.webmanifest';
        head.appendChild(link);
    }

    function resolveTabFromQuery() {
        var tab = parseQuery().tab;
        if (!tab) return null;
        return String(tab).toLowerCase();
    }

    function notifyWalletRouter() {
        var tab = resolveTabFromQuery();
        if (!tab) return;
        window.dispatchEvent(new CustomEvent('wallet-mobile-deeplink', { detail: { tab: tab } }));
    }

    window.MN2WalletMobile = {
        releaseTag: RELEASE_TAG,
        releaseApkName: RELEASE_APK_NAME,
        downloadDocPath: DOWNLOAD_DOC_PATH,
        appShellMode: appShellMode,
        isIos: isIos,
        isAndroid: isAndroid,
        isStandalone: isStandalone,
        isCapacitor: isCapacitor
    };

    if (!isWalletPage()) return;

    applyShellClass();
    injectManifest();
    notifyWalletRouter();
})();
