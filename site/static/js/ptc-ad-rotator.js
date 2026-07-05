/**
 * Sponsored click rotator for PTC campaigns.
 *
 * Looks for containers with data-ptc-placement, renders approved campaigns,
 * starts verified clicks, and dispatches ptc:reward-claimed when a reward is
 * credited so game/quest systems can react.
 */
(function () {
    'use strict';

    const BASE = (typeof window !== 'undefined' && window.location.origin) ? window.location.origin : '';
    const USER_ID = () => localStorage.getItem('game_user_id') || localStorage.getItem('mn_user_id') || 'default_user';

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function cardLabel(placement) {
        const labels = {
            home_smartlinks: 'Sponsored smart link',
            news_inline: 'Sponsored news link',
            aggregator_ideas: 'Traffic rotator',
            shop_mn2: 'Crypto sponsor',
            social_feed: 'Sponsored feed',
            click_quest: 'Sponsored click quest'
        };
        return labels[placement] || 'Sponsored';
    }

    async function postJson(url, body) {
        const res = await fetch(`${BASE}${url}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body || {})
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.success === false) {
            throw new Error(data.error || `Request failed (${res.status})`);
        }
        return data;
    }

    async function recordImpression(campaign, placement) {
        try {
            const data = await postJson('/api/ptc/impression', {
                campaign_id: campaign.id,
                placement,
                user_id: USER_ID()
            });
            return data.impression_id || '';
        } catch (err) {
            console.warn('[PTC] impression failed', err);
            return '';
        }
    }

    function notify(message, type) {
        if (window.gameNotifications && typeof window.gameNotifications.showNotification === 'function') {
            window.gameNotifications.showNotification(message, type || 'info');
            return;
        }
        if (window.showToast) {
            window.showToast(message, type || 'info');
            return;
        }
        console.log(`[PTC] ${message}`);
    }

    async function startSponsoredClick(campaign, placement, button, card) {
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = 'Opening...';
        try {
            const impressionId = card.dataset.impressionId || '';
            const start = await postJson('/api/ptc/click/start', {
                campaign_id: campaign.id,
                placement,
                user_id: USER_ID(),
                impression_id: impressionId
            });
            const target = start.redirect_url || start.destination_url;
            const opened = window.open(target, '_blank', 'noopener,noreferrer');
            if (!opened) {
                window.location.href = target;
                return;
            }
            const waitSeconds = Number(start.verify_after_seconds || 8);
            button.textContent = `Claim in ${waitSeconds}s`;
            let remaining = waitSeconds;
            const timer = window.setInterval(() => {
                remaining -= 1;
                if (remaining > 0) {
                    button.textContent = `Claim in ${remaining}s`;
                    return;
                }
                window.clearInterval(timer);
                button.disabled = false;
                button.textContent = `Claim +${start.reward_points || campaign.reward_points || 0}`;
                button.onclick = () => verifySponsoredClick(start.click_id, campaign, placement, button);
            }, 1000);
        } catch (err) {
            button.disabled = false;
            button.textContent = originalText;
            notify(err.message || 'Could not start sponsored click', 'error');
        }
    }

    async function verifySponsoredClick(clickId, campaign, placement, button) {
        button.disabled = true;
        button.textContent = 'Verifying...';
        try {
            const result = await postJson('/api/ptc/click/verify', {
                click_id: clickId,
                user_id: USER_ID()
            });
            const reward = Number(result.reward_points || 0);
            button.textContent = result.already_credited ? 'Already claimed' : `Claimed +${reward}`;
            button.classList.add('ptc-claimed');
            notify(result.already_credited ? 'Sponsored click already claimed.' : `Sponsored click reward: +${reward} PTC points`, 'success');
            window.dispatchEvent(new CustomEvent('ptc:reward-claimed', {
                detail: {
                    campaign,
                    placement,
                    click_id: clickId,
                    reward_points: reward,
                    reward_kind: result.reward_kind || 'internal_points'
                }
            }));
        } catch (err) {
            button.disabled = false;
            button.textContent = 'Try claim again';
            notify(err.message || 'Sponsored click verification failed', 'error');
        }
    }

    function renderCampaign(container, campaign, placement) {
        const card = document.createElement('article');
        card.className = 'ptc-card';
        card.innerHTML = `
            <div class="ptc-card-label">${escapeHtml(cardLabel(placement))}</div>
            <h3>${escapeHtml(campaign.title)}</h3>
            <p>${escapeHtml(campaign.description)}</p>
            <div class="ptc-card-meta">
                <span>${escapeHtml(campaign.advertiser || 'Sponsor')}</span>
                <span>+${Number(campaign.reward_points || 0)} PTC points</span>
            </div>
            <button type="button" class="ptc-card-cta">${escapeHtml(campaign.cta || 'Visit')}</button>
            <p class="ptc-disclosure">Sponsored link. Opens in a new tab; reward requires a short verified visit.</p>
        `;
        const button = card.querySelector('.ptc-card-cta');
        button.addEventListener('click', () => startSponsoredClick(campaign, placement, button, card));
        container.appendChild(card);
        recordImpression(campaign, placement).then((impressionId) => {
            if (impressionId) card.dataset.impressionId = impressionId;
        });
    }

    async function loadPlacement(container) {
        const placement = container.dataset.ptcPlacement || 'home_smartlinks';
        const limit = container.dataset.ptcLimit || '2';
        container.classList.add('ptc-slot');
        container.innerHTML = '<div class="ptc-loading">Loading sponsored links...</div>';
        try {
            const res = await fetch(`${BASE}/api/ptc/rotator?placement=${encodeURIComponent(placement)}&limit=${encodeURIComponent(limit)}&user_id=${encodeURIComponent(USER_ID())}`);
            const data = await res.json();
            const campaigns = data && data.success ? (data.campaigns || []) : [];
            if (!campaigns.length) {
                container.innerHTML = '';
                return;
            }
            container.innerHTML = '';
            const grid = document.createElement('div');
            grid.className = 'ptc-card-grid';
            container.appendChild(grid);
            campaigns.forEach((campaign) => renderCampaign(grid, campaign, placement));
        } catch (err) {
            console.warn('[PTC] placement failed', placement, err);
            container.innerHTML = '';
        }
    }

    function init() {
        document.querySelectorAll('[data-ptc-placement]').forEach(loadPlacement);
    }

    window.MasterNoderPTC = {
        init,
        loadPlacement
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
