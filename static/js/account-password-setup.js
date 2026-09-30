/**
 * A+ account password setup — guided unlock progress, confirm field, change-password flow.
 * Mount on #account-password-setup (profile) or any container via AccountPasswordSetup.mount().
 */
(function (global) {
    'use strict';

    function resolveUserId(explicit) {
        if (explicit) return explicit;
        return global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || 'default_user';
    }

    function esc(text) {
        var d = global.document.createElement('div');
        d.textContent = text == null ? '' : String(text);
        return d.innerHTML;
    }

    function strengthScore(password) {
        if (!password) return 0;
        var score = 0;
        if (password.length >= 6) score += 1;
        if (password.length >= 10) score += 1;
        if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
        if (/\d/.test(password)) score += 1;
        if (/[^A-Za-z0-9]/.test(password)) score += 1;
        return Math.min(score, 4);
    }

    function strengthColor(score) {
        if (score <= 1) return '#ff8888';
        if (score === 2) return '#fbbf24';
        if (score === 3) return '#00d4ff';
        return '#00ff88';
    }

    function post(path, body) {
        return fetch(path, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {}),
        }).then(function (r) {
            return r.json().then(function (data) {
                return { ok: r.ok, status: r.status, data: data };
            });
        });
    }

    function getStatus(userId) {
        return fetch('/api/auth/password/status?user_id=' + encodeURIComponent(userId), {
            credentials: 'same-origin',
        }).then(function (r) { return r.json(); });
    }

    function renderProgress(progress, rule) {
        var pct = (progress && progress.overall_percent) || 0;
        var gp = (progress && progress.game_points) || 0;
        var minGp = (progress && progress.min_game_points) || (rule && rule.min_game_points) || 50;
        var inv = (progress && progress.investigations) || 0;
        var minInv = (progress && progress.min_investigations) || (rule && rule.min_investigations) || 1;
        return '' +
            '<div class="aps-progress">' +
                '<div class="aps-progress-label"><span>Unlock progress</span><span>' + pct + '%</span></div>' +
                '<div class="aps-progress-bar" aria-hidden="true"><div class="aps-progress-fill" style="width:' + pct + '%"></div></div>' +
                '<p class="aps-policy">Earn <strong>' + esc(minGp) + '</strong> game_points (you have <strong>' + esc(gp) + '</strong>) or complete <strong>' + esc(minInv) + '</strong> Star Map investigation(s) (you have <strong>' + esc(inv) + '</strong>).</p>' +
            '</div>';
    }

    function renderSteps(state) {
        var steps = [
            { id: 'unlock', label: '1. Unlock' },
            { id: 'set', label: '2. Set password' },
            { id: 'done', label: '3. Protected' },
        ];
        return '<div class="aps-steps">' + steps.map(function (step) {
            var cls = 'aps-step';
            if (state === 'protected' && step.id === 'done') cls += ' done';
            else if (state === 'protected' && (step.id === 'unlock' || step.id === 'set')) cls += ' done';
            else if (state === 'ready' && step.id === 'unlock') cls += ' done';
            else if (state === 'ready' && step.id === 'set') cls += ' active';
            else if (state === 'locked' && step.id === 'unlock') cls += ' active';
            return '<div class="' + cls + '">' + esc(step.label) + '</div>';
        }).join('') + '</div>';
    }

    function renderForm(mode, rewardPoints) {
        var isChange = mode === 'change';
        var currentField = isChange
            ? '<div class="aps-field"><label for="aps-current-password">Current password</label><input id="aps-current-password" type="password" autocomplete="current-password" placeholder="Current password"></div>'
            : '';
        var submitLabel = isChange ? 'Change password' : ('Set password' + (rewardPoints ? ' (+' + rewardPoints + ' pts)' : ''));
        return '' +
            '<div class="aps-form">' +
                currentField +
                '<div class="aps-field"><label for="aps-new-password">New password</label><input id="aps-new-password" type="password" autocomplete="new-password" placeholder="At least 6 characters" minlength="6"></div>' +
                '<div class="aps-strength" aria-hidden="true"><div class="aps-strength-fill" id="aps-strength-fill"></div></div>' +
                '<div class="aps-field"><label for="aps-confirm-password">Confirm password</label><input id="aps-confirm-password" type="password" autocomplete="new-password" placeholder="Re-enter new password" minlength="6"></div>' +
                '<div class="aps-actions">' +
                    '<button type="button" class="aps-btn primary" id="aps-save-btn">' + esc(submitLabel) + '</button>' +
                '</div>' +
            '</div>';
    }

    function renderRecovery() {
        return '' +
            '<details class="aps-recovery">' +
                '<summary>Forgot password? Recovery options</summary>' +
                '<div class="aps-recovery-body">' +
                    '<p class="aps-policy" id="aps-recovery-policy">Loading recovery policy…</p>' +
                    '<button type="button" class="aps-btn ghost" id="aps-recovery-request-btn">Request recovery token</button>' +
                    '<div class="aps-field"><label for="aps-recovery-token">Recovery token</label><input id="aps-recovery-token" type="text" placeholder="Paste token from email or dev response"></div>' +
                    '<div class="aps-field"><label for="aps-recovery-password">New password</label><input id="aps-recovery-password" type="password" placeholder="At least 6 characters"></div>' +
                    '<button type="button" class="aps-btn ghost" id="aps-recovery-reset-btn">Reset with token</button>' +
                '</div>' +
            '</details>';
    }

    function AccountPasswordSetup(container, options) {
        this.root = typeof container === 'string' ? global.document.getElementById(container) : container;
        this.options = options || {};
        this.userId = resolveUserId(this.options.userId);
        this.state = null;
        if (this.root) this.refresh();
    }

    AccountPasswordSetup.prototype.setMessage = function (text, kind) {
        var el = this.root && this.root.querySelector('#aps-message');
        if (!el) return;
        el.textContent = text || '';
        el.className = 'aps-message' + (kind ? ' ' + kind : '');
    };

    AccountPasswordSetup.prototype.wireStrength = function () {
        var self = this;
        var input = this.root.querySelector('#aps-new-password');
        var fill = this.root.querySelector('#aps-strength-fill');
        if (!input || !fill || input._apsWired) return;
        input._apsWired = true;
        input.addEventListener('input', function () {
            var score = strengthScore(input.value || '');
            fill.style.width = (score / 4 * 100) + '%';
            fill.style.background = strengthColor(score);
        });
    };

    AccountPasswordSetup.prototype.wireActions = function () {
        var self = this;
        var saveBtn = this.root.querySelector('#aps-save-btn');
        var unlockBtn = this.root.querySelector('#aps-unlock-btn');
        var recoveryRequestBtn = this.root.querySelector('#aps-recovery-request-btn');
        var recoveryResetBtn = this.root.querySelector('#aps-recovery-reset-btn');

        if (saveBtn && !saveBtn._apsWired) {
            saveBtn._apsWired = true;
            saveBtn.addEventListener('click', function () { self.savePassword(); });
        }
        if (unlockBtn && !unlockBtn._apsWired) {
            unlockBtn._apsWired = true;
            unlockBtn.addEventListener('click', function () { self.checkUnlock(); });
        }
        if (recoveryRequestBtn && !recoveryRequestBtn._apsWired) {
            recoveryRequestBtn._apsWired = true;
            recoveryRequestBtn.addEventListener('click', function () { self.requestRecovery(); });
        }
        if (recoveryResetBtn && !recoveryResetBtn._apsWired) {
            recoveryResetBtn._apsWired = true;
            recoveryResetBtn.addEventListener('click', function () { self.resetWithRecovery(); });
        }
        this.wireStrength();
    };

    AccountPasswordSetup.prototype.render = function (data) {
        if (!this.root || !data || !data.success) {
            if (this.root) this.root.innerHTML = '<p class="aps-message error">Could not load password status.</p>';
            return;
        }
        this.state = data;
        var hasPassword = !!data.has_password;
        var canSet = !!data.can_set_password;
        var reward = (data.reward_on_set && data.reward_on_set.game_points) || 0;
        var progress = data.unlock_progress || {};
        var rule = data.unlock_rule || {};
        var recovery = data.recovery || {};
        var uiState = hasPassword ? 'protected' : (canSet ? 'ready' : 'locked');
        var badgeClass = hasPassword ? 'protected' : (canSet ? 'ready' : 'locked');
        var badgeText = hasPassword ? 'Protected' : (canSet ? 'Ready to set' : 'Locked');

        var headline = '';
        if (hasPassword) {
            headline = 'Your account is protected. Use the form below to change your password (current password required).';
            if (data.set_at) headline += ' Last set ' + data.set_at.slice(0, 10) + '.';
        } else if (data.fast_track && data.fast_track_reason) {
            headline = 'Fast track unlocked — you can set a password now because you have ' + data.fast_track_reason + '.';
        } else if (canSet) {
            headline = 'Password setup is unlocked. Choose a strong password and confirm it below.';
            if (reward) headline += ' First-time reward: +' + reward + ' game_points.';
        } else {
            headline = 'Complete the unlock requirement below, then set your password in one step.';
        }

        var body = '';
        if (!hasPassword && !canSet) {
            body += renderProgress(progress, rule);
            body += '<div class="aps-actions"><button type="button" class="aps-btn secondary" id="aps-unlock-btn">Check unlock</button></div>';
        } else {
            body += renderForm(hasPassword ? 'change' : 'set', reward);
        }

        var recoveryPolicy = 'Recovery: ';
        var methods = [];
        if (recovery.has_email) methods.push('email ' + (recovery.email_masked || 'on file'));
        if (recovery.provider) methods.push(recovery.provider + ' provider');
        recoveryPolicy += methods.length ? methods.join(' and ') : 'add email or link a provider on your profile';
        recoveryPolicy += '. ' + (recovery.email_delivery_configured
            ? 'Email delivery is configured.'
            : 'Tokens are shown here until SMTP is configured.');

        this.root.innerHTML =
            '<div class="aps-root">' +
                renderSteps(uiState) +
                '<span class="aps-badge ' + badgeClass + '">' + esc(badgeText) + '</span>' +
                '<p class="aps-status">' + esc(headline) + '</p>' +
                body +
                '<p class="aps-message" id="aps-message" role="status" aria-live="polite"></p>' +
                renderRecovery() +
                '<p class="aps-policy" id="aps-recovery-policy-inline">' + esc(recoveryPolicy) + '</p>' +
            '</div>';

        var policyEl = this.root.querySelector('#aps-recovery-policy');
        if (policyEl) policyEl.textContent = recoveryPolicy;
        this.wireActions();
    };

    AccountPasswordSetup.prototype.refresh = function () {
        var self = this;
        if (!this.root) return Promise.resolve();
        this.userId = resolveUserId(this.options.userId);
        this.root.innerHTML = '<p class="aps-status">Loading password setup…</p>';
        return getStatus(this.userId).then(function (data) {
            self.render(data);
            if (self.options.onRefresh) self.options.onRefresh(data);
            return data;
        }).catch(function () {
            if (self.root) self.root.innerHTML = '<p class="aps-message error">Failed to load password status.</p>';
        });
    };

    AccountPasswordSetup.prototype.checkUnlock = function () {
        var self = this;
        this.setMessage('Checking unlock…', 'info');
        return post('/api/auth/password/unlock', { user_id: this.userId }).then(function (res) {
            if (!res.data.success) {
                self.setMessage(res.data.error || 'Unlock requirement not met yet.', 'error');
                return self.refresh();
            }
            self.setMessage('Unlocked — you can set your password now.', 'success');
            return self.refresh();
        }).catch(function () {
            self.setMessage('Unlock check failed.', 'error');
        });
    };

    AccountPasswordSetup.prototype.savePassword = function () {
        var self = this;
        var current = (this.root.querySelector('#aps-current-password') || {}).value || '';
        var password = (this.root.querySelector('#aps-new-password') || {}).value || '';
        var confirm = (this.root.querySelector('#aps-confirm-password') || {}).value || '';
        var hasPassword = this.state && this.state.has_password;

        if (password.length < 6) {
            this.setMessage('Password must be at least 6 characters.', 'error');
            return;
        }
        if (password !== confirm) {
            this.setMessage('Passwords do not match. Re-enter confirmation.', 'error');
            return;
        }
        if (hasPassword && !current) {
            this.setMessage('Enter your current password to change it.', 'error');
            return;
        }

        this.setMessage('Saving password…', 'info');
        var payload = { user_id: this.userId, password: password };
        if (hasPassword) payload.current_password = current;

        return post('/api/auth/password/set', payload).then(function (res) {
            if (!res.data.success) {
                self.setMessage(res.data.error || 'Could not save password.', 'error');
                return;
            }
            var msg = res.data.message || 'Password saved.';
            if (res.data.points_awarded) msg += ' +' + res.data.points_awarded + ' game_points.';
            self.setMessage(msg, 'success');
            if (self.options.onSaved) self.options.onSaved(res.data);
            return self.refresh();
        }).catch(function () {
            self.setMessage('Save failed — try again.', 'error');
        });
    };

    AccountPasswordSetup.prototype.requestRecovery = function () {
        var self = this;
        this.setMessage('Creating recovery request…', 'info');
        return post('/api/auth/password/recovery/request', { user_id: this.userId }).then(function (res) {
            if (!res.data.success) {
                self.setMessage(res.data.error || 'Recovery request failed.', 'error');
                return;
            }
            var tokenInput = self.root.querySelector('#aps-recovery-token');
            if (res.data.reset_token && tokenInput) tokenInput.value = res.data.reset_token;
            self.setMessage(res.data.message || 'Recovery token created.', 'success');
        }).catch(function () {
            self.setMessage('Recovery request failed.', 'error');
        });
    };

    AccountPasswordSetup.prototype.resetWithRecovery = function () {
        var self = this;
        var token = (this.root.querySelector('#aps-recovery-token') || {}).value || '';
        var password = (this.root.querySelector('#aps-recovery-password') || {}).value || '';
        if (!token.trim()) {
            this.setMessage('Recovery token is required.', 'error');
            return;
        }
        if (password.length < 6) {
            this.setMessage('Password must be at least 6 characters.', 'error');
            return;
        }
        this.setMessage('Resetting password…', 'info');
        return post('/api/auth/password/recovery/reset', {
            user_id: this.userId,
            token: token,
            password: password,
        }).then(function (res) {
            if (!res.data.success) {
                self.setMessage(res.data.error || 'Password reset failed.', 'error');
                return;
            }
            self.setMessage('Password reset successfully.', 'success');
            if (self.options.onSaved) self.options.onSaved(res.data);
            return self.refresh();
        }).catch(function () {
            self.setMessage('Password reset failed.', 'error');
        });
    };

    AccountPasswordSetup.mount = function (containerId, options) {
        return new AccountPasswordSetup(containerId, options);
    };

    global.AccountPasswordSetup = AccountPasswordSetup;
})(typeof window !== 'undefined' ? window : this);
