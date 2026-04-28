/**
 * Game ↔ Battle bridge: shared snapshot + local user profiling (display name, combat focus).
 * Mount: <section data-mn-game-battle-bridge data-variant="game|battle"></section>
 */
(function () {
    'use strict';

    var LS_NAME = 'mn_profile_display_name';
    var LS_FOCUS = 'mn_profile_combat_focus';

    function injectStylesOnce() {
        if (document.getElementById('mn-gbb-styles')) return;
        var css = document.createElement('style');
        css.id = 'mn-gbb-styles';
        css.textContent = [
            '.mn-gbb{font-family:inherit;border-radius:14px;padding:18px 20px;margin:0 auto 20px;',
            'max-width:min(100%,1600px);box-sizing:border-box;border:1px solid rgba(0,255,136,0.28);background:rgba(0,0,0,0.42);}',
            '.mn-gbb--battle{border-color:rgba(0,255,136,0.35);}',
            '.mn-gbb-inner{color:rgba(255,255,255,0.92);}',
            '.mn-gbb-head{display:flex;flex-wrap:wrap;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:14px;}',
            '.mn-gbb-title{margin:0;font-size:1.15rem;color:#00ff88;font-weight:700;}',
            '.mn-gbb--battle .mn-gbb-title{color:var(--battle-primary,#00ff88);}',
            '.mn-gbb-sub{margin:4px 0 0;font-size:0.88rem;opacity:0.88;line-height:1.45;}',
            '.mn-gbb-meta{font-size:0.78rem;opacity:0.65;margin-top:6px;}',
            '.mn-gbb-prefs{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-end;margin-bottom:14px;padding:12px;',
            'background:rgba(0,0,0,0.35);border-radius:10px;border:1px solid rgba(255,255,255,0.08);}',
            '.mn-gbb-prefs label{display:flex;flex-direction:column;gap:4px;font-size:0.75rem;opacity:0.85;}',
            '.mn-gbb-prefs input,.mn-gbb-prefs select{padding:8px 10px;border-radius:8px;border:1px solid rgba(0,255,136,0.35);',
            'background:rgba(10,12,20,0.9);color:#fff;min-width:160px;}',
            '.mn-gbb-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin-bottom:14px;}',
            '.mn-gbb-card{background:rgba(15,18,28,0.9);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:12px 14px;}',
            '.mn-gbb-card h3{margin:0 0 8px;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.06em;opacity:0.75;color:#7fdbff;}',
            '.mn-gbb-stat{font-size:1.35rem;font-weight:800;color:#fff;}',
            '.mn-gbb-bar{height:6px;border-radius:4px;background:rgba(255,255,255,0.08);margin-top:6px;overflow:hidden;}',
            '.mn-gbb-bar>span{display:block;height:100%;border-radius:4px;background:linear-gradient(90deg,#00ff88,#00d4ff);}',
            '.mn-gbb-actions{display:flex;flex-wrap:wrap;gap:10px;align-items:center;}',
            '.mn-gbb-btn{display:inline-block;padding:10px 16px;border-radius:8px;font-weight:600;text-decoration:none;',
            'border:1px solid rgba(0,255,136,0.5);color:#00ff88;background:rgba(0,255,136,0.12);cursor:pointer;font-size:0.9rem;}',
            '.mn-gbb--battle .mn-gbb-btn{border-color:rgba(0,255,136,0.55);color:var(--battle-primary,#00ff88);background:rgba(0,255,136,0.1);}',
            '.mn-gbb-btn.secondary{border-color:rgba(0,212,255,0.45);color:#00d4ff;background:rgba(0,212,255,0.08);}',
            '.mn-gbb-loading,.mn-gbb-err{margin:0;font-size:0.95rem;}',
            '.mn-gbb-err{color:#ff6b8a;}'
        ].join('');
        document.head.appendChild(css);
    }

    function getUserId() {
        try {
            return localStorage.getItem('game_user_id') || 'default_user';
        } catch (e) {
            return 'default_user';
        }
    }

    function focusLine(persona, focus) {
        var base = (persona && persona.cross_link_hint) ? String(persona.cross_link_hint) : '';
        if (focus === 'hunter_skew') return 'Hunter-first pacing: ' + base;
        if (focus === 'battle_skew') return 'Battle-first pacing: ' + base;
        return base;
    }

    function barPct(n, maxv) {
        if (!maxv || maxv < 1) return 0;
        return Math.min(100, Math.round((Number(n) || 0) / maxv * 100));
    }

    function render(host, variant, data) {
        var inner = host.querySelector('.mn-gbb-inner') || host;
        var hunter = data.hunter || {};
        var battle = data.battle || {};
        var points = data.points || {};
        var persona = data.persona || {};
        var stats = (hunter.stats) || {};
        var keys = ['creativity', 'efficiency', 'quality', 'social', 'knowledge'];
        var maxv = 1;
        keys.forEach(function (k) {
            maxv = Math.max(maxv, Number(stats[k]) || 0);
        });

        var dname = '';
        var focus = 'balanced';
        try {
            dname = localStorage.getItem(LS_NAME) || '';
            focus = localStorage.getItem(LS_FOCUS) || 'balanced';
        } catch (e) {}

        var showName = dname.trim() || 'Your profile';
        var isGame = variant === 'game';
        var primaryCta = isGame
            ? '<a class="mn-gbb-btn" href="/battle">Open Battle Arena</a>'
            : '<a class="mn-gbb-btn" href="/game">Open Hunter Game</a>';
        var secondaryCta = '<a class="mn-gbb-btn secondary" href="/profile?tab=points">Profile hub</a>';
        var refreshBtn = '<button type="button" class="mn-gbb-btn secondary" data-mn-gbb-refresh>Refresh snapshot</button>';

        var signalBars = keys.map(function (k) {
            var v = Number(stats[k]) || 0;
            var pct = barPct(v, maxv);
            return '<div style="margin-bottom:8px;"><span style="font-size:0.75rem;opacity:0.8;">' + k + '</span>' +
                '<div class="mn-gbb-bar"><span style="width:' + pct + '%;"></span></div></div>';
        }).join('');

        inner.innerHTML =
            '<div class="mn-gbb-head">' +
            '<div><h2 class="mn-gbb-title">' + (isGame ? '⚔️ Linked battle profile' : '🎮 Linked hunter profile') + '</h2>' +
            '<p class="mn-gbb-sub"><strong>' + escapeHtml(showName) + '</strong> · same <code>game_user_id</code> as Profile &amp; Shop' +
            '</p><p class="mn-gbb-meta">Archetype: <strong style="color:#7fdbff;">' + escapeHtml(persona.archetype || '—') + '</strong> · ' +
            escapeHtml(persona.arena_voice || '') + '</p></div>' +
            '<div style="text-align:right;"><span class="mn-gbb-stat" style="font-size:2rem;">' + (persona.readiness_score != null ? persona.readiness_score : '—') + '</span>' +
            '<div style="font-size:0.75rem;opacity:0.75;">Readiness</div></div></div>' +

            '<div class="mn-gbb-prefs">' +
            '<label>Display name (local)<input type="text" maxlength="48" data-mn-gbb-dname placeholder="e.g. Star cadet" value="' + escapeAttr(dname) + '"></label>' +
            '<label>Combat focus (local)<select data-mn-gbb-focus>' +
            '<option value="balanced"' + (focus === 'balanced' ? ' selected' : '') + '>Balanced</option>' +
            '<option value="hunter_skew"' + (focus === 'hunter_skew' ? ' selected' : '') + '>Hunter / XP skew</option>' +
            '<option value="battle_skew"' + (focus === 'battle_skew' ? ' selected' : '') + '>Battle / arena skew</option>' +
            '</select></label></div>' +

            '<p class="mn-gbb-sub" style="margin-bottom:12px;">' + escapeHtml(focusLine(persona, focus)) + '</p>' +

            '<div class="mn-gbb-grid">' +
            '<div class="mn-gbb-card"><h3>Hunter row</h3><div class="mn-gbb-stat">Lv ' + escapeHtml(String(hunter.level != null ? hunter.level : '—')) + '</div>' +
            '<div style="font-size:0.88rem;opacity:0.9;margin-top:6px;">' + escapeHtml(hunter.title || '') + '</div>' +
            '<div style="font-size:0.8rem;opacity:0.75;margin-top:4px;">Hunter XP (track): ' + (hunter.total_xp != null ? Number(hunter.total_xp).toLocaleString() : '—') + '</div></div>' +

            '<div class="mn-gbb-card"><h3>Arena row</h3><div class="mn-gbb-stat">' + escapeHtml(String(battle.wins != null ? battle.wins : 0)) + 'W / ' +
            escapeHtml(String(battle.losses != null ? battle.losses : 0)) + 'L</div>' +
            '<div style="font-size:0.8rem;opacity:0.75;margin-top:6px;">Win rate ' + escapeHtml(String(battle.win_rate != null ? battle.win_rate : 0)) + '% · Battles ' +
            escapeHtml(String(battle.total_battles != null ? battle.total_battles : 0)) + '</div>' +
            '<div style="font-size:0.8rem;margin-top:4px;">Battle pts (unified): <strong>' +
            (points.battle_points != null ? Number(points.battle_points).toLocaleString() : '—') + '</strong></div></div>' +

            '<div class="mn-gbb-card"><h3>Economy slice</h3><div style="font-size:0.85rem;line-height:1.55;">Coins: <strong>' +
            (points.coins != null ? Number(points.coins).toLocaleString() : '—') + '</strong><br>Game pts: <strong>' +
            (points.game_points != null ? Number(points.game_points).toLocaleString() : '—') + '</strong><br>Trophy pts: <strong>' +
            (points.trophy_points != null ? Number(points.trophy_points).toLocaleString() : '—') + '</strong></div></div>' +

            (function () {
                var lc = data.lab_progress || data.lab_chapter2 || {};
                var c = lc.researched_count != null ? lc.researched_count : 0;
                var t = lc.total != null ? lc.total : 25;
                var b = lc.bonuses_claimed != null ? lc.bonuses_claimed : 0;
                var tier = lc.lab_tier ? String(lc.lab_tier) : '—';
                var ex = lc.exploration_count != null ? lc.exploration_count : 0;
                return '<div class="mn-gbb-card"><h3>Lab progression</h3><div class="mn-gbb-stat">' + c + ' / ' + t + '</div>' +
                    '<div style="font-size:0.82rem;opacity:0.85;margin-top:6px;">Tier: <strong>' + escapeHtml(tier) + '</strong> · Explores ' + ex + '</div>' +
                    '<div style="font-size:0.78rem;opacity:0.7;margin-top:4px;">First-touch bonuses claimed: ' + b + '</div>' +
                    '<div style="margin-top:10px;"><a class="mn-gbb-btn secondary" href="/lab" style="display:inline-block;padding:8px 12px;font-size:0.8rem;">Open Lab</a></div></div>';
            })() +

            '<div class="mn-gbb-card"><h3>Stat signals</h3>' + signalBars + '</div>' +
            '</div>' +

            '<div class="mn-gbb-actions">' + primaryCta + secondaryCta + refreshBtn + '</div>';

        var dnameInput = inner.querySelector('[data-mn-gbb-dname]');
        var focusSel = inner.querySelector('[data-mn-gbb-focus]');
        if (dnameInput) {
            dnameInput.addEventListener('blur', function () {
                try {
                    localStorage.setItem(LS_NAME, dnameInput.value.trim().slice(0, 48));
                } catch (e) {}
                render(host, variant, data);
            });
        }
        if (focusSel) {
            focusSel.addEventListener('change', function () {
                try {
                    localStorage.setItem(LS_FOCUS, focusSel.value || 'balanced');
                } catch (e) {}
                render(host, variant, data);
            });
        }
        var rb = inner.querySelector('[data-mn-gbb-refresh]');
        if (rb) rb.addEventListener('click', function () { mount(host); });
    }

    function escapeHtml(s) {
        if (s == null || s === '') return '';
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function escapeAttr(s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/</g, '&lt;');
    }

    function mount(host) {
        injectStylesOnce();
        var variant = (host.getAttribute('data-variant') || 'game').toLowerCase();
        host.classList.add('mn-gbb');
        host.classList.toggle('mn-gbb--battle', variant === 'battle');
        host.classList.toggle('mn-gbb--game', variant !== 'battle');
        host.innerHTML = '<div class="mn-gbb-inner"><p class="mn-gbb-loading">Loading profile bridge…</p></div>';

        var url = '/api/game/hunters/battle-bridge-snapshot?user_id=' + encodeURIComponent(getUserId());
        fetch(url)
            .then(function (r) { return r.json(); })
            .then(function (d) {
                if (!d || !d.success) {
                    host.querySelector('.mn-gbb-inner').innerHTML = '<p class="mn-gbb-err">Could not load bridge snapshot.</p>';
                    return;
                }
                render(host, variant, d);
            })
            .catch(function () {
                host.querySelector('.mn-gbb-inner').innerHTML = '<p class="mn-gbb-err">Network error loading bridge.</p>';
            });
    }

    function boot() {
        injectStylesOnce();
        document.querySelectorAll('[data-mn-game-battle-bridge]').forEach(mount);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

    window.MNGameBattleBridge = { refresh: boot, mount: mount, getUserId: getUserId };
})();
