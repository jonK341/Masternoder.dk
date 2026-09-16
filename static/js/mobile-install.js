/**
 * Site-wide mobile install — PWA from the website (no Play Store / App Store).
 * Android: native install prompt when Chrome supports it.
 * iPhone: guided "Add to Home Screen" sheet (Safari has no programmatic install).
 */
(function () {
    'use strict';

    var DISMISS_KEY = 'mn_install_banner_dismissed';
    var deferredPrompt = null;

    function isMobilePhone() {
        var ua = navigator.userAgent || '';
        if (/Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua)) {
            return true;
        }
        return navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1;
    }

    function isIos() {
        var ua = navigator.userAgent || '';
        return /iPad|iPhone|iPod/.test(ua)
            || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    }

    function isAndroid() {
        return /Android/i.test(navigator.userAgent || '');
    }

    function isStandalone() {
        try {
            return window.matchMedia('(display-mode: standalone)').matches
                || window.navigator.standalone === true;
        } catch (e) {
            return false;
        }
    }

    function isCasinoPage() {
        return /^\/casino(\/|$)/.test(window.location.pathname || '');
    }

    function injectHeadTags() {
        if (document.querySelector('link[rel="manifest"][href="/manifest.webmanifest"]')) return;

        var head = document.head || document.getElementsByTagName('head')[0];
        if (!head) return;

        var link = document.createElement('link');
        link.rel = 'manifest';
        link.href = '/manifest.webmanifest';
        head.appendChild(link);

        var tags = [
            { name: 'mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-capable', content: 'yes' },
            { name: 'apple-mobile-web-app-status-bar-style', content: 'black-translucent' },
            { name: 'apple-mobile-web-app-title', content: 'MasterNoder' },
            { name: 'theme-color', content: '#1A1035' }
        ];
        tags.forEach(function (t) {
            if (document.querySelector('meta[name="' + t.name + '"]')) return;
            var meta = document.createElement('meta');
            meta.name = t.name;
            meta.content = t.content;
            head.appendChild(meta);
        });

        if (!document.querySelector('link[rel="apple-touch-icon"]')) {
            var icon = document.createElement('link');
            icon.rel = 'apple-touch-icon';
            icon.href = '/static/img/app/icon-192.svg';
            head.appendChild(icon);
        }
    }

    function registerServiceWorker() {
        if (!('serviceWorker' in navigator)) return;
        if (localStorage.getItem('sw_disabled') === '1') return;
        if (new URLSearchParams(location.search).get('sw') === '0') return;
        if (document.querySelector('script[src*="service-worker-gatherer"]')) return;

        navigator.serviceWorker.register('/service-worker.js', {
            scope: '/',
            updateViaCache: 'none'
        }).catch(function () { /* optional */ });
    }

    function dismissBanner(bar) {
        if (!bar) return;
        bar.classList.add('hidden');
        document.body.classList.remove('mn-install-banner-visible');
        try { sessionStorage.setItem(DISMISS_KEY, '1'); } catch (e) { /* */ }
    }

    function showIosSheet() {
        var existing = document.getElementById('mn-install-ios-sheet');
        if (existing) {
            existing.classList.remove('hidden');
            return;
        }

        var backdrop = document.createElement('div');
        backdrop.id = 'mn-install-ios-sheet';
        backdrop.className = 'mn-install-sheet-backdrop';
        backdrop.setAttribute('role', 'dialog');
        backdrop.setAttribute('aria-modal', 'true');
        backdrop.setAttribute('aria-label', 'Install on iPhone');
        backdrop.innerHTML =
            '<div class="mn-install-sheet">'
            + '<h2>Install MasterNoder on iPhone</h2>'
            + '<p style="margin:0 0 0.5rem;font-size:0.88rem;opacity:0.9;">No App Store needed — add the site to your home screen:</p>'
            + '<ol>'
            + '<li>Tap the <strong>Share</strong> button in Safari (square with arrow).</li>'
            + '<li>Scroll and tap <strong>Add to Home Screen</strong>.</li>'
            + '<li>Tap <strong>Add</strong> — MasterNoder opens like an app.</li>'
            + '</ol>'
            + '<button type="button" class="mn-install-sheet-close">Got it</button>'
            + '</div>';

        backdrop.addEventListener('click', function (e) {
            if (e.target === backdrop) backdrop.classList.add('hidden');
        });
        backdrop.querySelector('.mn-install-sheet-close').addEventListener('click', function () {
            backdrop.classList.add('hidden');
        });

        document.body.appendChild(backdrop);
    }

    function buildBanner() {
        if (!isMobilePhone() || isStandalone() || isCasinoPage()) return;
        try {
            if (sessionStorage.getItem(DISMISS_KEY) === '1') return;
        } catch (e) { /* */ }
        if (document.getElementById('mn-install-banner')) return;

        var bar = document.createElement('div');
        bar.id = 'mn-install-banner';
        bar.className = 'mn-install-banner';
        bar.setAttribute('role', 'region');
        bar.setAttribute('aria-label', 'Install MasterNoder app');

        var ctaLabel = isIos() ? 'How to install' : (deferredPrompt ? 'Install app' : 'Add to home screen');
        var hint = isIos()
            ? 'Add MasterNoder to your home screen — works like a native app.'
            : 'Install from this website — no Play Store required.';

        bar.innerHTML =
            '<img class="mn-install-banner-icon" src="/static/img/app/icon-192.svg" alt="" width="44" height="44">'
            + '<div class="mn-install-banner-text">'
            + '<strong>Get MasterNoder app</strong>'
            + '<span>' + hint + '</span>'
            + '</div>'
            + '<div class="mn-install-banner-actions">'
            + '<button type="button" class="mn-install-banner-cta" id="mn-install-cta">' + ctaLabel + '</button>'
            + '<button type="button" class="mn-install-banner-dismiss" aria-label="Dismiss">✕</button>'
            + '</div>';

        bar.querySelector('.mn-install-banner-dismiss').addEventListener('click', function () {
            dismissBanner(bar);
        });

        bar.querySelector('#mn-install-cta').addEventListener('click', async function () {
            if (isIos()) {
                showIosSheet();
                return;
            }
            if (deferredPrompt) {
                deferredPrompt.prompt();
                try { await deferredPrompt.userChoice; } catch (e) { /* ignore */ }
                deferredPrompt = null;
                dismissBanner(bar);
                return;
            }
            if (isAndroid()) {
                showIosSheet();
                var sheet = document.getElementById('mn-install-ios-sheet');
                if (sheet) {
                    sheet.querySelector('h2').textContent = 'Install on Android';
                    var ol = sheet.querySelector('ol');
                    if (ol) {
                        ol.innerHTML =
                            '<li>Open Chrome menu (⋮) at the top right.</li>'
                            + '<li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>'
                            + '<li>Confirm — MasterNoder opens full-screen like an app.</li>';
                    }
                }
            }
        });

        document.body.appendChild(bar);
        document.body.classList.add('mn-install-banner-visible');
    }

    function triggerInstall() {
        if (isIos()) {
            showIosSheet();
            return;
        }
        if (deferredPrompt) {
            deferredPrompt.prompt();
            deferredPrompt.userChoice.catch(function () {});
            return;
        }
        showIosSheet();
        var sheet = document.getElementById('mn-install-ios-sheet');
        if (sheet && isAndroid()) {
            sheet.querySelector('h2').textContent = 'Install on Android';
            var ol = sheet.querySelector('ol');
            if (ol) {
                ol.innerHTML =
                    '<li>Open Chrome menu (⋮) at the top right.</li>'
                    + '<li>Tap <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li>'
                    + '<li>Confirm — MasterNoder opens full-screen like an app.</li>';
            }
        }
    }

    window.__mnInstallPwa = triggerInstall;

    function boot() {
        injectHeadTags();
        registerServiceWorker();

        window.addEventListener('beforeinstallprompt', function (e) {
            e.preventDefault();
            deferredPrompt = e;
            var bar = document.getElementById('mn-install-banner');
            var cta = document.getElementById('mn-install-cta');
            if (cta && !isIos()) cta.textContent = 'Install app';
            if (!bar && isMobilePhone() && !isStandalone() && !isCasinoPage()) {
                buildBanner();
            }
        });

        buildBanner();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
