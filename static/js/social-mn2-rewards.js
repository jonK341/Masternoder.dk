/**
 * MN2 social rewards panel — claim signup/chat/referral rewards.
 */
(function (global) {
    'use strict';

    function uid() {
        return global.localStorage.getItem('game_user_id')
            || global.localStorage.getItem('user_id')
            || 'default_user';
    }

    function escapeHtml(value) {
        return String(value || '').replace(/[&<>"']/g, function (ch) {
            return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch];
        });
    }

    function renderRewards(container, options, onClaimed) {
        if (!container) return;
        if (!options || !options.length) {
            container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">No reward options available.</p>';
            return;
        }
        container.innerHTML = options.map(function (opt) {
            var state = opt.claimed ? 'Claimed' : (opt.ready ? 'Claim' : 'Locked');
            var color = opt.claimed ? '#00ff88' : (opt.ready ? '#FFD700' : 'rgba(255,255,255,0.45)');
            var disabled = opt.ready ? '' : ' disabled';
            var requires = opt.requires && Object.keys(opt.requires).length
                ? Object.keys(opt.requires).map(function (k) { return k + ': ' + opt.requires[k]; }).join(', ')
                : 'signup';
            return '<div class="mn2-reward-card">' +
                '<strong>' + escapeHtml(opt.name) + '</strong>' +
                '<p>' + escapeHtml(opt.description) + '</p>' +
                '<div class="mn2-reward-row"><span class="mn2-reward-amt" style="color:' + color + '">' + escapeHtml(opt.reward_mn2) + ' MN2</span>' +
                '<button type="button" class="social-reward-claim" data-option-id="' + escapeHtml(opt.id) + '"' + disabled + ' style="border-color:' + color + ';color:' + color + ';">' + state + '</button></div>' +
                '<small>Requires: ' + escapeHtml(requires) + '</small></div>';
        }).join('');

        container.querySelectorAll('.social-reward-claim:not([disabled])').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var optionId = btn.getAttribute('data-option-id');
                if (!optionId) return;
                btn.disabled = true;
                btn.textContent = 'Claiming…';
                fetch('/api/social/rewards/claim', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: uid(), option_id: optionId }),
                }).then(function (r) { return r.json(); }).then(function (d) {
                    if (d.success && typeof onClaimed === 'function') onClaimed(d);
                    else {
                        btn.disabled = false;
                        btn.textContent = d.error || 'Failed';
                    }
                }).catch(function () {
                    btn.disabled = false;
                    btn.textContent = 'Failed';
                });
            });
        });
    }

    function loadPanel(opts) {
        opts = opts || {};
        var rewardsEl = opts.rewardsEl;
        var referralEl = opts.referralEl;
        var balanceEl = opts.balanceEl;
        var userId = uid();
        var base = global.location.origin || '';

        var tasks = [
            fetch(base + '/api/social/rewards/status?user_id=' + encodeURIComponent(userId)).then(function (r) { return r.json(); }),
        ];
        if (global.Mn2SiteBridge) {
            tasks.push(global.Mn2SiteBridge.loadBalance());
        }

        return Promise.all(tasks).then(function (results) {
            var rewardData = results[0];
            var bal = results[1];
            if (balanceEl && bal && bal.success && global.Mn2SiteBridge) {
                balanceEl.textContent = global.Mn2SiteBridge.fmtMn2(bal.mn2_balance, 4) + ' MN2';
            }
            if (rewardData && rewardData.success) {
                var options = rewardData.crypto && rewardData.crypto.options ? rewardData.crypto.options : [];
                renderRewards(rewardsEl, options, function () { loadPanel(opts); });
                if (referralEl) {
                    referralEl.innerHTML =
                        '<p style="margin:0 0 8px;font-size:0.88rem;color:var(--text-secondary);">Share your referral link — signups unlock MN2 rewards.</p>' +
                        '<code style="color:#00ff88;word-break:break-all;">' + escapeHtml(rewardData.referral_link || '') + '</code>' +
                        '<p style="margin:8px 0 0;font-size:0.82rem;">Code: <strong style="color:#00d4ff;">' + escapeHtml(rewardData.referral_code || '') + '</strong></p>';
                }
            }
            return rewardData;
        });
    }

    global.SocialMn2Rewards = { loadPanel: loadPanel, renderRewards: renderRewards };
})(window);
