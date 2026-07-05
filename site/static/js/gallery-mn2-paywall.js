/**
 * Gallery MN2 paywall — premium/ultra previews require unlock or 24h pass.
 */
(function (global) {
    'use strict';

    var bridge = global.Mn2SiteBridge;
    var state = {
        prices: { premium: 0.05, ultra: 0.1 },
        passPrice: 0.25,
        unlocked: {},
        passActive: false,
        passExpiresAt: null,
    };

    function uid() {
        return bridge ? bridge.uid() : (global.localStorage.getItem('game_user_id') || 'default_user');
    }

    function fmt(n) {
        return bridge ? bridge.fmtMn2(n) : String(n);
    }

    function gatedQuality(level) {
        var q = (level || '').toLowerCase();
        return state.prices[q] != null ? q : null;
    }

    function isUnlocked(videoId) {
        if (state.passActive) return true;
        return !!state.unlocked[String(videoId)];
    }

    function loadStatus() {
        return fetch('/api/gallery/premium/status?user_id=' + encodeURIComponent(uid()))
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d.success) return;
                state.passActive = !!d.pass_active;
                state.passExpiresAt = d.pass_expires_at || null;
                state.prices = d.prices || state.prices;
                state.passPrice = d.pass_price_mn2 != null ? d.pass_price_mn2 : state.passPrice;
                state.unlocked = {};
                (d.unlocked_video_ids || []).forEach(function (id) { state.unlocked[String(id)] = true; });
                updateStrip();
            }).catch(function () { /* ignore */ });
    }

    function loadConfig() {
        return fetch('/api/gallery/premium/config').then(function (r) { return r.json(); }).then(function (d) {
            if (!d.success) return;
            state.prices = d.prices || state.prices;
            state.passPrice = d.pass_price_mn2 != null ? d.pass_price_mn2 : state.passPrice;
            updateStrip();
        }).catch(function () { /* ignore */ });
    }

    function updateStrip() {
        var passEl = global.document.getElementById('gallery-mn2-pass');
        var priceEl = global.document.getElementById('gallery-mn2-prices');
        if (passEl) {
            passEl.textContent = state.passActive
                ? ('Day pass active' + (state.passExpiresAt ? ' · until ' + new Date(state.passExpiresAt).toLocaleString() : ''))
                : (fmt(state.passPrice) + ' MN2 · 24h all premium');
        }
        if (priceEl) {
            var parts = Object.keys(state.prices).map(function (k) {
                return k + ': ' + fmt(state.prices[k]) + ' MN2';
            });
            priceEl.textContent = parts.join(' · ') || '—';
        }
    }

    function refreshBalance() {
        if (!bridge) return Promise.resolve();
        return bridge.loadBalance().then(function (d) {
            var bal = (d && (d.balance != null ? d.balance : d.mn2_balance)) || 0;
            var el = global.document.getElementById('gallery-mn2-balance');
            if (el) el.textContent = fmt(bal) + ' MN2';
        }).catch(function () {
            var el = global.document.getElementById('gallery-mn2-balance');
            if (el) el.textContent = '—';
        });
    }

    function buyPass() {
        return new Promise(function (resolve) {
            var existing = global.document.getElementById('gallery-mn2-paywall-modal');
            if (existing) existing.remove();
            var modal = global.document.createElement('div');
            modal.id = 'gallery-mn2-paywall-modal';
            modal.className = 'gallery-mn2-paywall-modal';
            modal.innerHTML =
                '<div class="gallery-mn2-paywall-card">' +
                '<h3>Gallery 24h MN2 pass</h3>' +
                '<p>Unlock all premium and ultra previews for <strong>' + fmt(state.passPrice) + ' MN2</strong> (24 hours).</p>' +
                '<div class="gallery-mn2-paywall-actions">' +
                '<button type="button" id="gallery-unlock-pass-confirm">Buy pass (' + fmt(state.passPrice) + ')</button>' +
                '<a href="/shop">Shop MN2</a>' +
                '<button type="button" id="gallery-unlock-cancel" class="secondary">Cancel</button>' +
                '</div>' +
                '<p id="gallery-paywall-status" class="gallery-paywall-status"></p>' +
                '</div>';
            global.document.body.appendChild(modal);

            function close(result) {
                modal.remove();
                resolve(result);
            }

            modal.addEventListener('click', function (e) {
                if (e.target === modal) close(false);
            });
            global.document.getElementById('gallery-unlock-cancel').addEventListener('click', function () { close(false); });
            var statusEl = global.document.getElementById('gallery-paywall-status');
            global.document.getElementById('gallery-unlock-pass-confirm').addEventListener('click', function () {
                var btn = this;
                btn.disabled = true;
                statusEl.textContent = 'Processing…';
                fetch('/api/gallery/premium/unlock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: uid(), pass: true }),
                }).then(function (r) { return r.json(); }).then(function (d) {
                    if (d.success) {
                        loadStatus().then(function () { refreshBalance(); close(true); });
                    } else {
                        statusEl.textContent = d.error || 'Unlock failed';
                        btn.disabled = false;
                    }
                }).catch(function () {
                    statusEl.textContent = 'Network error';
                    btn.disabled = false;
                });
            });
        });
    }

    function showPaywallModal(video, quality, price) {
        return new Promise(function (resolve) {
            var existing = global.document.getElementById('gallery-mn2-paywall-modal');
            if (existing) existing.remove();
            var modal = global.document.createElement('div');
            modal.id = 'gallery-mn2-paywall-modal';
            modal.className = 'gallery-mn2-paywall-modal';
            modal.innerHTML =
                '<div class="gallery-mn2-paywall-card">' +
                '<h3>Premium preview · pay with MN2</h3>' +
                '<p><strong>' + (video.title || 'Video') + '</strong> is <em>' + quality + '</em> quality.</p>' +
                '<p>Unlock this video for <strong>' + fmt(price) + ' MN2</strong>, or get a 24h pass for <strong>' + fmt(state.passPrice) + ' MN2</strong>.</p>' +
                '<div class="gallery-mn2-paywall-actions">' +
                '<button type="button" id="gallery-unlock-one">Unlock video (' + fmt(price) + ')</button>' +
                '<button type="button" id="gallery-unlock-pass">24h pass (' + fmt(state.passPrice) + ')</button>' +
                '<a href="/shop">Shop MN2</a>' +
                '<button type="button" id="gallery-unlock-cancel" class="secondary">Cancel</button>' +
                '</div>' +
                '<p id="gallery-paywall-status" class="gallery-paywall-status"></p>' +
                '</div>';
            global.document.body.appendChild(modal);

            function close(result) {
                modal.remove();
                resolve(result);
            }

            modal.addEventListener('click', function (e) {
                if (e.target === modal) close(false);
            });
            global.document.getElementById('gallery-unlock-cancel').addEventListener('click', function () { close(false); });

            function unlock(body, statusEl, btn) {
                btn.disabled = true;
                statusEl.textContent = 'Processing…';
                fetch('/api/gallery/premium/unlock', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(Object.assign({ user_id: uid() }, body)),
                }).then(function (r) { return r.json(); }).then(function (d) {
                    if (d.success) {
                        return loadStatus().then(function () { refreshBalance(); close(true); });
                    }
                    statusEl.textContent = d.error || 'Unlock failed';
                    btn.disabled = false;
                }).catch(function () {
                    statusEl.textContent = 'Network error';
                    btn.disabled = false;
                });
            }

            var statusEl = global.document.getElementById('gallery-paywall-status');
            global.document.getElementById('gallery-unlock-one').addEventListener('click', function () {
                unlock({ video_id: String(video.id) }, statusEl, this);
            });
            global.document.getElementById('gallery-unlock-pass').addEventListener('click', function () {
                unlock({ pass: true }, statusEl, this);
            });
        });
    }

    /**
     * Returns true if preview may proceed (already unlocked or not gated).
     */
    function gateBeforePreview(video) {
        var quality = gatedQuality(video && video.quality_level);
        if (!quality) return Promise.resolve(true);
        if (isUnlocked(video.id)) return Promise.resolve(true);
        var price = state.prices[quality];
        return showPaywallModal(video, quality, price);
    }

    function init() {
        loadConfig();
        loadStatus();
        refreshBalance();
        if (bridge) {
            bridge.loadPrice().then(function (d) {
                var p = d && (d.price_usd != null ? d.price_usd : d.usd);
                var el = global.document.getElementById('gallery-mn2-rate');
                if (el) el.textContent = p != null ? ('$' + Number(p).toFixed(4) + ' / MN2') : '—';
            }).catch(function () { /* ignore */ });
        }
        var passBtn = global.document.getElementById('gallery-mn2-buy-pass');
        if (passBtn) {
            passBtn.addEventListener('click', function () { buyPass(); });
        }
    }

    global.GalleryMn2Paywall = {
        init: init,
        gateBeforePreview: gateBeforePreview,
        refreshBalance: refreshBalance,
        loadStatus: loadStatus,
    };
    global.document.addEventListener('DOMContentLoaded', init);
})(window);
