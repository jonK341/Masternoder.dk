/**
 * Creator mobile: install banner, Capacitor hooks, PWA prompt, store links.
 */
(function () {
    'use strict';

    var APK_URL = '/static/downloads/masternoder-creator.apk';

    var deferredPrompt = null;

    function isIos() {
        return /iPad|iPhone|iPod/.test(navigator.userAgent)
            || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
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

    window.__creatorInstallPwa = function () {
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function () { deferredPrompt = null; });
            return;
        }
        if (isIos()) {
            alert('Tap Share → Add to Home Screen to install Super Encoder.');
        }
    };

    window.addEventListener('beforeinstallprompt', function (e) {
        e.preventDefault();
        deferredPrompt = e;
    });

    function wireCapacitor() {
        if (!window.Capacitor || !window.Capacitor.Plugins) return;
        var App = window.Capacitor.Plugins.App;
        if (!App || !App.addListener) return;
        document.body.classList.add('cr-capacitor-shell');
        App.addListener('appUrlOpen', function (event) {
            if (event && event.url) {
                try {
                    var u = new URL(event.url.replace(/^masternoder:\/\//, 'https://masternoder.dk/'));
                    if (u.pathname.indexOf('/creator') >= 0) {
                        window.location.href = u.pathname + u.search + u.hash;
                    }
                } catch (err) { /* optional */ }
            }
        });
    }

    function loadApkUrl() {
        fetch(window.location.origin + '/api/creator/mobile/config')
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success && data.download_apk_url) APK_URL = data.download_apk_url;
            }).catch(function () { /* optional */ });
    }

    document.addEventListener('DOMContentLoaded', function () {
        if (isCapacitor()) wireCapacitor();
        loadApkUrl();
        var q = window.location.search || '';
        if (q.indexOf('app=creator-capacitor') >= 0 || q.indexOf('app=creator-pwa') >= 0) {
            document.body.classList.add('cr-app-shell');
        }
    });
})();
