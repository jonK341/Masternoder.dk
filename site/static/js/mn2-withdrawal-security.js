/**
 * Withdrawal security UI — whitelist addresses + TOTP 2FA setup.
 * Expects container #mn2-withdraw-security and optional withdraw form with totp field.
 */
(function (global) {
    'use strict';

    function post(path, body) {
        return fetch(path, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        }).then(function (r) { return r.json(); });
    }

    function get(path) {
        return fetch(path, { credentials: 'same-origin' }).then(function (r) { return r.json(); });
    }

    function renderList(container, addresses) {
        if (!container) return;
        if (!addresses || !addresses.length) {
            container.innerHTML = '<p style="opacity:0.7;margin:0;">No whitelisted addresses yet.</p>';
            return;
        }
        container.innerHTML = addresses.map(function (addr) {
            return '<div style="display:flex;gap:8px;align-items:center;margin:4px 0;">' +
                '<code style="flex:1;font-size:0.78rem;">' + addr + '</code>' +
                '<button type="button" data-remove-whitelist="' + addr + '" style="padding:4px 8px;border-radius:6px;border:1px solid #ff8888;background:transparent;color:#ff8888;cursor:pointer;">Remove</button>' +
                '</div>';
        }).join('');
        container.querySelectorAll('[data-remove-whitelist]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                post('/api/mn2/withdraw/whitelist', { action: 'remove', address: btn.getAttribute('data-remove-whitelist') })
                    .then(refresh);
            });
        });
    }

    function refresh() {
        var root = global.document.getElementById('mn2-withdraw-security');
        if (!root) return;
        get('/api/mn2/withdraw/security').then(function (d) {
            if (!d.success) return;
            var list = root.querySelector('#mn2-whitelist-list');
            renderList(list, d.whitelist || []);
            var totpEl = root.querySelector('#mn2-2fa-status');
            if (totpEl) {
                totpEl.textContent = d.totp_enabled ? '2FA enabled' : (d.totp_configured ? '2FA pending verification' : '2FA off');
            }
            var req = root.querySelector('#mn2-whitelist-required');
            if (req) req.textContent = d.withdrawal_requires_whitelist ? 'Whitelist required for withdrawals' : 'Whitelist optional';
        }).catch(function () {});
    }

    function init() {
        var root = global.document.getElementById('mn2-withdraw-security');
        if (!root) return;

        var addBtn = root.querySelector('#mn2-whitelist-add');
        var addrInput = root.querySelector('#mn2-whitelist-address');
        if (addBtn && addrInput) {
            addBtn.addEventListener('click', function () {
                post('/api/mn2/withdraw/whitelist', { action: 'add', address: addrInput.value.trim() })
                    .then(function () { addrInput.value = ''; refresh(); });
            });
        }

        var setupBtn = root.querySelector('#mn2-2fa-setup');
        if (setupBtn) {
            setupBtn.addEventListener('click', function () {
                post('/api/mn2/withdraw/2fa/setup').then(function (d) {
                    var secretEl = root.querySelector('#mn2-2fa-secret');
                    if (secretEl && d.secret) secretEl.textContent = d.secret;
                    if (d.otpauth_uri) global.prompt('Scan in authenticator app:\n' + d.otpauth_uri);
                });
            });
        }

        var enableBtn = root.querySelector('#mn2-2fa-enable');
        if (enableBtn) {
            enableBtn.addEventListener('click', function () {
                var code = (root.querySelector('#mn2-2fa-code') || {}).value || '';
                post('/api/mn2/withdraw/2fa/enable', { code: code }).then(refresh);
            });
        }

        refresh();
    }

    global.Mn2WithdrawalSecurity = { init: init, refresh: refresh };
    global.document.addEventListener('DOMContentLoaded', init);
})(window);
