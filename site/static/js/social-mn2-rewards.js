/**
 * MN2 social rewards panel — claim signup/chat/referral rewards + earn rate surfacing.
 */
(function (global) {
    'use strict';

    var SOCIAL_ACTION_LABELS = {
        first_post: 'First feed post',
        post_created: 'Each new post',
        like_received: 'Like on your post',
        routed_chat: 'AI-assisted chat',
        llm_insight: 'LLM insight',
        evaluate_output: 'Output evaluation',
    };

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

    function renderEarnRates(container, agentInfo, claimOptions) {
        if (!container) return;
        var mn2 = (agentInfo && agentInfo.actions_mn2) || {};
        var coins = (agentInfo && agentInfo.actions_coins) || {};
        var cap = agentInfo && agentInfo.daily_cap_mn2 != null ? agentInfo.daily_cap_mn2 : '—';
        var rows = [];

        Object.keys(SOCIAL_ACTION_LABELS).forEach(function (action) {
            if (mn2[action] == null && coins[action] == null) return;
            rows.push({
                label: SOCIAL_ACTION_LABELS[action],
                mn2: mn2[action] || 0,
                coins: coins[action] || 0,
                kind: 'auto',
            });
        });

        (claimOptions || []).forEach(function (opt) {
            rows.push({
                label: opt.name,
                mn2: opt.reward_mn2,
                coins: 0,
                kind: 'claim',
                description: opt.description,
            });
        });

        if (!rows.length) {
            container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">Earn rates unavailable.</p>';
            return;
        }

        container.innerHTML =
            '<p style="margin:0 0 8px;font-size:0.82rem;color:var(--text-secondary);">Daily agent MN2 cap: <strong style="color:#00d4ff;">' + escapeHtml(cap) + '</strong></p>' +
            '<div class="earn-rate-grid">' +
            rows.map(function (row) {
                var coinTxt = row.coins ? (' · +' + row.coins + ' coins') : '';
                var desc = row.description ? ('<span>' + escapeHtml(row.description) + '</span>') : '';
                return '<div class="earn-rate-row">' +
                    '<strong>' + escapeHtml(row.label) + '</strong>' +
                    desc +
                    '<span class="earn-rate-amt">+' + escapeHtml(row.mn2) + ' MN2' + coinTxt + '</span>' +
                    '</div>';
            }).join('') +
            '</div>';
    }

    function loadPanel(opts) {
        opts = opts || {};
        var rewardsEl = opts.rewardsEl;
        var referralEl = opts.referralEl;
        var balanceEl = opts.balanceEl;
        var earnEl = opts.earnEl;
        var userId = uid();
        var base = global.location.origin || '';

        var tasks = [
            fetch(base + '/api/social/rewards/status?user_id=' + encodeURIComponent(userId)).then(function (r) { return r.json(); }),
            fetch(base + '/api/agents/rewards/info').then(function (r) { return r.json(); }).catch(function () { return null; }),
        ];
        if (global.Mn2SiteBridge) {
            tasks.push(global.Mn2SiteBridge.loadBalance());
        }

        return Promise.all(tasks).then(function (results) {
            var rewardData = results[0];
            var agentInfo = results[1];
            var bal = results[2];
            if (balanceEl && bal && bal.success && global.Mn2SiteBridge) {
                balanceEl.textContent = global.Mn2SiteBridge.fmtMn2(bal.mn2_balance, 4) + ' MN2';
            }
            var options = [];
            if (rewardData && rewardData.success) {
                options = rewardData.crypto && rewardData.crypto.options ? rewardData.crypto.options : [];
                renderRewards(rewardsEl, options, function () { loadPanel(opts); });
                if (referralEl) {
                    referralEl.innerHTML =
                        '<p style="margin:0 0 8px;font-size:0.88rem;color:var(--text-secondary);">Share your referral link — signups unlock MN2 rewards.</p>' +
                        '<code style="color:#00ff88;word-break:break-all;">' + escapeHtml(rewardData.referral_link || '') + '</code>' +
                        '<p style="margin:8px 0 0;font-size:0.82rem;">Code: <strong style="color:#00d4ff;">' + escapeHtml(rewardData.referral_code || '') + '</strong></p>';
                }
            }
            if (earnEl && agentInfo) {
                renderEarnRates(earnEl, agentInfo, options);
            }
            return rewardData;
        });
    }

    function showRewardToast(reward) {
        if (!reward) return;
        var mn2 = reward.mn2_awarded != null ? reward.mn2_awarded : reward.amount;
        var coins = reward.coins_awarded;
        var parts = [];
        if (mn2 != null && Number(mn2) > 0) parts.push('+' + mn2 + ' MN2');
        if (coins != null && Number(coins) > 0) parts.push('+' + coins + ' coins');
        if (!parts.length) return;
        var msg = 'Agent reward: ' + parts.join(', ');
        if (global.showToast) global.showToast('Earned', msg, 'success');
        else if (global.toast && global.toast.success) global.toast.success(msg);
    }

    function renderEarnCoach(container, earnCoach) {
        if (!container) return;
        if (!earnCoach || !(earnCoach.tips && earnCoach.tips.length) && !earnCoach.summary) {
            container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">No earn tips right now — explore social actions to unlock rewards.</p>';
            return;
        }
        var html = '';
        if (earnCoach.summary) {
            html += '<p style="margin:0 0 10px;font-size:0.88rem;color:#00d4ff;">' + escapeHtml(earnCoach.summary) + '</p>';
        }
        if (earnCoach.tips && earnCoach.tips.length) {
            html += '<div class="earn-rate-grid">' + earnCoach.tips.map(function (tip) {
                var mn2 = tip.mn2 != null ? ('<span class="earn-rate-amt">+' + escapeHtml(tip.mn2) + ' MN2</span>') : '';
                return '<div class="earn-rate-row"><strong>' + escapeHtml(tip.label) + '</strong><span>' + escapeHtml(tip.reason || '') + '</span>' + mn2 + '</div>';
            }).join('') + '</div>';
        }
        container.innerHTML = html;
    }

    function loadEarnCoach(container, userId, refresh) {
        if (!container) return Promise.resolve(null);
        var base = global.location.origin || '';
        var url = base + '/api/social/agent/recommendations?user_id=' + encodeURIComponent(userId || uid()) + '&coach=1';
        if (refresh) url += '&refresh=1';
        return fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.success && data.earn_coach) {
                    renderEarnCoach(container, data.earn_coach);
                    if (data.earn_coach.reward) showRewardToast(data.earn_coach.reward);
                } else {
                    container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">Earn coach unavailable.</p>';
                }
                return data;
            })
            .catch(function () {
                container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">Earn coach unavailable.</p>';
                return null;
            });
    }

    function bindEarnCoachRefresh(opts) {
        opts = opts || {};
        var btn = opts.btn;
        var panelEl = opts.panelEl;
        var userId = opts.userId || uid();
        if (!btn || !panelEl) return;
        btn.addEventListener('click', function () {
            btn.disabled = true;
            var prev = btn.textContent;
            btn.textContent = 'Refreshing…';
            loadEarnCoach(panelEl, userId, true).finally(function () {
                btn.disabled = false;
                btn.textContent = prev;
            });
        });
    }

    function renderChatMessages(container, messages) {
        if (!container) return;
        if (!messages || !messages.length) {
            container.innerHTML = '<p style="color:var(--text-secondary);margin:0;">No social chat messages yet. Say hello!</p>';
            return;
        }
        var nearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 48;
        container.innerHTML = messages.map(function (msg) {
            var ts = msg.created_at
                ? new Date(msg.created_at).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
                : '';
            var isAi = msg.is_ai || msg.user_id === 'ai_copilot';
            var nameColor = isAi ? '#FFD700' : 'var(--primary, #00d4ff)';
            var prefix = isAi ? '🤖 ' : '';
            var bodyStyle = isAi ? 'color:rgba(255,215,0,0.92);' : '';
            return '<div class="social-chat-row" style="padding:7px 0;border-bottom:1px solid rgba(255,255,255,0.06);">' +
                '<strong style="color:' + nameColor + ';">' + prefix + escapeHtml(msg.display_name || msg.user_id) + '</strong> ' +
                '<span style="color:rgba(255,255,255,0.45);font-size:0.75rem;">' + escapeHtml(ts) + '</span>' +
                '<div style="margin-top:2px;' + bodyStyle + '">' + escapeHtml(msg.message) + '</div></div>';
        }).join('');
        if (nearBottom) container.scrollTop = container.scrollHeight;
    }

    var _chatPollTimer = null;
    var _chatPollState = {};

    function _chatFeedKey(feedEl) {
        return (feedEl && (feedEl.id || feedEl.dataset.chatFeedKey)) || 'default';
    }

    function _chatSnapshot(messages) {
        var msgs = messages || [];
        var latest = msgs.length ? msgs[msgs.length - 1] : null;
        return {
            count: msgs.length,
            latestId: latest && latest.id != null ? String(latest.id) : '',
        };
    }

    function _chatChanged(feedEl, messages) {
        var key = _chatFeedKey(feedEl);
        var snap = _chatSnapshot(messages);
        var prev = _chatPollState[key];
        if (!prev || prev.count !== snap.count || prev.latestId !== snap.latestId) {
            _chatPollState[key] = snap;
            return true;
        }
        return false;
    }

    function stopSocialChatPoll() {
        if (_chatPollTimer) {
            clearInterval(_chatPollTimer);
            _chatPollTimer = null;
        }
    }

    function startSocialChatPoll(feedEl, userId, intervalMs) {
        stopSocialChatPoll();
        if (!feedEl) return;
        var ms = intervalMs || 15000;
        _chatPollTimer = setInterval(function () {
            loadSocialChat(feedEl, userId);
        }, ms);
    }

    function loadSocialChat(feedEl, userId, limit, forceRender) {
        if (!feedEl) return Promise.resolve(null);
        var base = global.location.origin || '';
        return fetch(base + '/api/social/chat/messages?limit=' + (limit || 30))
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.success) {
                    var messages = data.messages || [];
                    if (forceRender || _chatChanged(feedEl, messages)) {
                        renderChatMessages(feedEl, messages);
                    }
                } else if (forceRender || !feedEl.dataset.chatLoaded) {
                    feedEl.innerHTML = '<p style="color:var(--text-secondary);margin:0;">Could not load chat.</p>';
                }
                if (data && data.success) feedEl.dataset.chatLoaded = '1';
                return data;
            })
            .catch(function () {
                if (forceRender || !feedEl.dataset.chatLoaded) {
                    feedEl.innerHTML = '<p style="color:var(--text-secondary);margin:0;">Could not load chat.</p>';
                }
                return null;
            });
    }

    function initSocialChatPanel(opts) {
        opts = opts || {};
        var feedEl = opts.feedEl;
        var userId = opts.userId || uid();
        if (!feedEl) return;
        loadSocialChat(feedEl, userId, opts.limit, true);
        if (opts.poll !== false) {
            startSocialChatPoll(feedEl, userId, opts.intervalMs || 15000);
        }
        bindSocialChat({
            feedEl: feedEl,
            inputEl: opts.inputEl,
            sendBtn: opts.sendBtn,
            aiToggleEl: opts.aiToggleEl,
            userId: userId,
            onSent: opts.onSent,
        });
    }

    function bindSocialChat(opts) {
        opts = opts || {};
        var feedEl = opts.feedEl;
        var inputEl = opts.inputEl;
        var sendBtn = opts.sendBtn;
        var aiToggleEl = opts.aiToggleEl;
        var userId = opts.userId || uid();
        var onSent = opts.onSent;
        if (!sendBtn || sendBtn.dataset.bound) return;
        sendBtn.dataset.bound = '1';
        var base = global.location.origin || '';
        function doSend() {
            var message = inputEl ? inputEl.value.trim() : '';
            if (!message) return;
            var wantAi = aiToggleEl && aiToggleEl.checked;
            sendBtn.disabled = true;
            fetch(base + '/api/social/chat/send', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, message: message, ai_reply: wantAi }),
            }).then(function (r) { return r.json(); }).then(function (d) {
                sendBtn.disabled = false;
                if (d.success) {
                    if (inputEl) inputEl.value = '';
                    if (d.reward) showRewardToast(d.reward);
                    loadSocialChat(feedEl, userId);
                    if (typeof onSent === 'function') onSent(d);
                } else if (global.showToast) {
                    global.showToast('Chat', d.error || 'Failed', 'error');
                }
            }).catch(function () {
                sendBtn.disabled = false;
            });
        }
        sendBtn.addEventListener('click', doSend);
        if (inputEl) {
            inputEl.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    doSend();
                }
            });
        }
    }

    function copyTextToClipboard(text, onDone) {
        if (!text) return;
        if (global.navigator && global.navigator.clipboard && global.navigator.clipboard.writeText) {
            global.navigator.clipboard.writeText(text).then(function () {
                if (typeof onDone === 'function') onDone(true);
            }).catch(function () {
                if (typeof onDone === 'function') onDone(false);
            });
            return;
        }
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        try {
            document.execCommand('copy');
            if (typeof onDone === 'function') onDone(true);
        } catch (e) {
            if (typeof onDone === 'function') onDone(false);
        }
        document.body.removeChild(ta);
    }

    function bindSocialAiDraft(opts) {
        opts = opts || {};
        var btn = opts.btn;
        var textareaEl = opts.textareaEl;
        var toneEl = opts.toneEl;
        var userId = opts.userId || uid();
        if (!btn || btn.dataset.bound) return;
        btn.dataset.bound = '1';
        btn.addEventListener('click', function () {
            btn.disabled = true;
            if (toneEl) toneEl.disabled = true;
            var prevHtml = btn.innerHTML;
            btn.classList.add('is-loading');
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Drafting…';
            var hint = textareaEl ? textareaEl.value.trim() : '';
            var tone = toneEl ? toneEl.value : (opts.tone || 'casual');
            fetch((global.location.origin || '') + '/api/social/posts/ai-draft', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, hint: hint || undefined, tone: tone || 'casual' }),
            }).then(function (r) { return r.json(); }).then(function (d) {
                btn.disabled = false;
                if (toneEl) toneEl.disabled = false;
                btn.classList.remove('is-loading');
                btn.innerHTML = prevHtml;
                if (d.success && d.draft) {
                    if (textareaEl) textareaEl.value = d.draft;
                    if (d.reward) showRewardToast(d.reward);
                } else if (global.showToast) {
                    global.showToast('AI draft', d.error || 'Failed', 'error');
                }
            }).catch(function () {
                btn.disabled = false;
                if (toneEl) toneEl.disabled = false;
                btn.classList.remove('is-loading');
                btn.innerHTML = prevHtml;
                if (global.showToast) global.showToast('AI draft', 'Could not generate draft', 'error');
            });
        });
    }

    function bindSocialTabShareLinks(opts) {
        opts = opts || {};
        var buttons = opts.buttons;
        var path = opts.path || '/social';
        var defaultTab = opts.defaultTab || 'friends';
        if (!buttons || !buttons.length) return;
        var origin = global.location.origin || '';
        Array.prototype.forEach.call(buttons, function (btn) {
            if (!btn || btn.dataset.shareBound) return;
            btn.dataset.shareBound = '1';
            btn.addEventListener('click', function (e) {
                e.stopPropagation();
                e.preventDefault();
                var tab = btn.getAttribute('data-tab') || btn.dataset.tab || defaultTab;
                var url = origin + path + (tab === defaultTab ? '' : '?tab=' + encodeURIComponent(tab));
                copyTextToClipboard(url, function (ok) {
                    var prev = btn.textContent;
                    btn.textContent = ok ? 'Copied!' : 'Failed';
                    setTimeout(function () { btn.textContent = prev; }, 2000);
                    if (ok && global.showToast) global.showToast('Link copied', 'Tab link copied to clipboard', 'success');
                    else if (!ok && global.showToast) global.showToast('Copy link', 'Could not copy link', 'error');
                });
            });
        });
    }

    function onChatStreamEvent(evt) {
        if (evt && evt.type === 'done' && evt.reward) showRewardToast(evt.reward);
    }

    function bindPromoGenerator(opts) {
        opts = opts || {};
        var btn = opts.btn;
        var outputEl = opts.outputEl;
        var userId = opts.userId || uid();
        if (!btn || !outputEl) return;
        btn.addEventListener('click', function () {
            btn.disabled = true;
            var prev = btn.textContent;
            btn.textContent = 'Generating…';
            fetch((global.location.origin || '') + '/api/social/referrals/promo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId }),
            }).then(function (r) { return r.json(); }).then(function (data) {
                btn.disabled = false;
                btn.textContent = prev;
                if (!data.success) {
                    outputEl.innerHTML = '<p style="color:#ff6b6b;margin:0;">' + escapeHtml(data.error || 'Failed') + '</p>';
                    return;
                }
                var links = (data.share_links || []).map(function (lnk) {
                    var color = escapeHtml(lnk.color || 'rgba(0,212,255,0.25)');
                    return '<a href="' + escapeHtml(lnk.url || '#') + '" target="_blank" rel="noopener" style="padding:6px 12px;border-radius:8px;text-decoration:none;font-weight:600;background:' + color + ';color:#fff;margin:4px 4px 0 0;display:inline-block;">' + escapeHtml(lnk.icon || lnk.name || 'Share') + '</a>';
                }).join('');
                var promoText = data.promo_text || '';
                outputEl.innerHTML =
                    '<p id="social-promo-text" style="margin:0 0 8px;font-size:0.88rem;color:var(--text-primary);white-space:pre-wrap;">' + escapeHtml(promoText) + '</p>' +
                    '<button type="button" class="social-promo-copy btn-action" style="margin-bottom:8px;">Copy promo text</button>' +
                    (links ? '<div style="margin-top:8px;">' + links + '</div>' : '');
                var copyBtn = outputEl.querySelector('.social-promo-copy');
                if (copyBtn) {
                    copyBtn.addEventListener('click', function () {
                        copyTextToClipboard(promoText, function (ok) {
                            copyBtn.textContent = ok ? 'Copied!' : 'Copy failed';
                            setTimeout(function () { copyBtn.textContent = 'Copy promo text'; }, 2000);
                        });
                    });
                }
                if (data.reward) showRewardToast(data.reward);
            }).catch(function () {
                btn.disabled = false;
                btn.textContent = prev;
                outputEl.innerHTML = '<p style="color:#ff6b6b;margin:0;">Could not generate promo text.</p>';
            });
        });
    }

    if (!global._socialChatPollUnloadBound) {
        global._socialChatPollUnloadBound = true;
        global.addEventListener('pagehide', stopSocialChatPoll);
    }

    global.SocialMn2Rewards = {
        loadPanel: loadPanel,
        renderRewards: renderRewards,
        renderEarnRates: renderEarnRates,
        renderEarnCoach: renderEarnCoach,
        loadEarnCoach: loadEarnCoach,
        bindEarnCoachRefresh: bindEarnCoachRefresh,
        renderChatMessages: renderChatMessages,
        loadSocialChat: loadSocialChat,
        initSocialChatPanel: initSocialChatPanel,
        startSocialChatPoll: startSocialChatPoll,
        stopSocialChatPoll: stopSocialChatPoll,
        bindSocialChat: bindSocialChat,
        bindSocialAiDraft: bindSocialAiDraft,
        bindSocialTabShareLinks: bindSocialTabShareLinks,
        bindPromoGenerator: bindPromoGenerator,
        showRewardToast: showRewardToast,
        onChatStreamEvent: onChatStreamEvent,
        copyTextToClipboard: copyTextToClipboard,
    };
})(window);
