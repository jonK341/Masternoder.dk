/**
 * Profile security status panel + email recovery UI helpers.
 */
(function (global) {
    'use strict';

    function esc(text) {
        var d = global.document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    }

    function resolveUserId() {
        return global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || 'default_user';
    }

    function indicator(label, value, level) {
        return '<div class="profile-security-indicator ' + esc(level) + '">' +
            '<div class="label">' + esc(label) + '</div>' +
            '<div class="value">' + esc(value) + '</div></div>';
    }

    function renderSecurityPanel(data) {
        var panel = global.document.getElementById('profile-security-status-panel');
        if (!panel || !data || !data.success) {
            if (panel) panel.textContent = 'Could not load security status.';
            return;
        }
        var pwd = data.has_password ? 'Set' : 'Not set';
        var pwdLevel = data.has_password ? 'ok' : 'warn';
        if (data.password_set_at) pwd += ' · ' + String(data.password_set_at).slice(0, 10);

        var email = data.email_verified ? ('Verified' + (data.email_masked ? ' (' + data.email_masked + ')' : '')) : (data.email_masked ? 'Unverified' : 'Missing');
        var emailLevel = data.email_verified ? 'ok' : (data.email_masked ? 'warn' : 'bad');

        var recovery = data.recovery_email_set ? 'Backup set' : 'Not set';
        var recoveryLevel = data.recovery_email_set ? 'ok' : 'warn';

        var session = data.session_bound ? 'Bound' : 'Local only';
        var sessionLevel = data.session_bound ? 'ok' : 'warn';

        panel.innerHTML =
            indicator('Password', pwd, pwdLevel) +
            indicator('Email', email, emailLevel) +
            indicator('Recovery email', recovery, recoveryLevel) +
            indicator('Session', session, sessionLevel);
    }

    function loadSecurityPanel(userId) {
        var uid = userId || resolveUserId();
        return fetch('/api/user/security/status?user_id=' + encodeURIComponent(uid), { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                renderSecurityPanel(data);
                return data;
            })
            .catch(function () {
                var panel = global.document.getElementById('profile-security-status-panel');
                if (panel) panel.textContent = 'Failed to load security status.';
            });
    }

    function postJson(path, body) {
        return fetch(path, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        }).then(function (r) {
            return r.json().then(function (data) { return { ok: r.ok, data: data }; });
        });
    }

    function wireEmailRecovery(userId) {
        var uid = userId || resolveUserId();
        var statusEl = global.document.getElementById('profile-email-recovery-status');
        var verifyBtn = global.document.getElementById('profile-email-verify-btn');
        var verifyConfirmBtn = global.document.getElementById('profile-email-verify-confirm-btn');
        var changeBtn = global.document.getElementById('profile-email-change-btn');
        var changeConfirmBtn = global.document.getElementById('profile-email-change-confirm-btn');
        var recoveryBtn = global.document.getElementById('profile-recovery-email-btn');
        var recoveryConfirmBtn = global.document.getElementById('profile-recovery-email-confirm-btn');
        var forgotBtn = global.document.getElementById('profile-forgot-password-btn');

        function setStatus(msg, kind) {
            if (!statusEl) return;
            statusEl.textContent = msg || '';
            statusEl.className = 'profile-email-recovery-status' + (kind ? ' ' + kind : '');
        }

        fetch('/api/auth/email/status?user_id=' + encodeURIComponent(uid), { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (!data.success) return;
                var parts = [];
                if (data.email_verified) parts.push('Primary email verified');
                else if (data.has_email) parts.push('Primary email pending verification');
                else parts.push('No verified email yet');
                if (data.recovery_email_verified) parts.push('recovery email set');
                setStatus(parts.join(' · ') + '.', data.email_verified ? 'ok' : 'warn');
            })
            .catch(function () { setStatus('Could not load email status.', 'bad'); });

        if (verifyBtn && !verifyBtn._wired) {
            verifyBtn._wired = true;
            verifyBtn.addEventListener('click', function () {
                var email = (global.document.getElementById('profile-email-verify-input') || {}).value || '';
                postJson('/api/auth/email/verify/request', { user_id: uid, email: email }).then(function (res) {
                    if (!res.data.success) { setStatus(res.data.error || 'Verification request failed.', 'bad'); return; }
                    if (res.data.verification_token) {
                        var tokenInput = global.document.getElementById('profile-email-verify-token');
                        if (tokenInput) tokenInput.value = res.data.verification_token;
                    }
                    setStatus(res.data.message || 'Verification sent.', 'ok');
                    loadSecurityPanel(uid);
                });
            });
        }

        if (verifyConfirmBtn && !verifyConfirmBtn._wired) {
            verifyConfirmBtn._wired = true;
            verifyConfirmBtn.addEventListener('click', function () {
                var token = (global.document.getElementById('profile-email-verify-token') || {}).value || '';
                postJson('/api/auth/email/verify/confirm', { user_id: uid, token: token }).then(function (res) {
                    setStatus(res.data.message || res.data.error || 'Done.', res.data.success ? 'ok' : 'bad');
                    if (res.data.success) loadSecurityPanel(uid);
                });
            });
        }

        if (changeBtn && !changeBtn._wired) {
            changeBtn._wired = true;
            changeBtn.addEventListener('click', function () {
                var email = (global.document.getElementById('profile-email-change-input') || {}).value || '';
                var password = (global.document.getElementById('profile-email-change-password') || {}).value || '';
                postJson('/api/auth/email/change/request', { user_id: uid, new_email: email, current_password: password }).then(function (res) {
                    if (!res.data.success) { setStatus(res.data.error || 'Change request failed.', 'bad'); return; }
                    if (res.data.change_token) {
                        var tokenInput = global.document.getElementById('profile-email-change-token');
                        if (tokenInput) tokenInput.value = res.data.change_token;
                    }
                    setStatus(res.data.message || 'Change email requested.', 'ok');
                });
            });
        }

        if (changeConfirmBtn && !changeConfirmBtn._wired) {
            changeConfirmBtn._wired = true;
            changeConfirmBtn.addEventListener('click', function () {
                var token = (global.document.getElementById('profile-email-change-token') || {}).value || '';
                postJson('/api/auth/email/change/confirm', { user_id: uid, token: token }).then(function (res) {
                    setStatus(res.data.message || res.data.error || 'Done.', res.data.success ? 'ok' : 'bad');
                    if (res.data.success) loadSecurityPanel(uid);
                });
            });
        }

        if (recoveryBtn && !recoveryBtn._wired) {
            recoveryBtn._wired = true;
            recoveryBtn.addEventListener('click', function () {
                var email = (global.document.getElementById('profile-recovery-email-input') || {}).value || '';
                postJson('/api/auth/email/recovery/request', { user_id: uid, recovery_email: email }).then(function (res) {
                    if (!res.data.success) { setStatus(res.data.error || 'Recovery email request failed.', 'bad'); return; }
                    if (res.data.recovery_token) {
                        var tokenInput = global.document.getElementById('profile-recovery-email-token');
                        if (tokenInput) tokenInput.value = res.data.recovery_token;
                    }
                    setStatus(res.data.message || 'Recovery email requested.', 'ok');
                    loadSecurityPanel(uid);
                });
            });
        }

        if (recoveryConfirmBtn && !recoveryConfirmBtn._wired) {
            recoveryConfirmBtn._wired = true;
            recoveryConfirmBtn.addEventListener('click', function () {
                var token = (global.document.getElementById('profile-recovery-email-token') || {}).value || '';
                postJson('/api/auth/email/recovery/confirm', { user_id: uid, token: token }).then(function (res) {
                    setStatus(res.data.message || res.data.error || 'Done.', res.data.success ? 'ok' : 'bad');
                    if (res.data.success) loadSecurityPanel(uid);
                });
            });
        }

        if (forgotBtn && !forgotBtn._wired) {
            forgotBtn._wired = true;
            forgotBtn.addEventListener('click', function () {
                var email = (global.document.getElementById('profile-forgot-password-email') || {}).value || '';
                postJson('/api/auth/password/recovery/request-by-email', { email: email }).then(function (res) {
                    setStatus(res.data.message || 'If an account exists, instructions were sent.', 'ok');
                });
            });
        }
    }

    function initProfileSecurity(userId) {
        document.querySelectorAll('[data-security-panel]').forEach(function (panel) {
            if (panel.getAttribute('data-security-panel') !== 'layers') {
                panel.style.display = 'none';
            }
        });
        loadSecurityPanel(userId);
        wireEmailRecovery(userId);
    }

    global.ProfileSecurity = {
        loadSecurityPanel: loadSecurityPanel,
        wireEmailRecovery: wireEmailRecovery,
        init: initProfileSecurity,
    };
})(typeof window !== 'undefined' ? window : this);
