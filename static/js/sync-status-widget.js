/**
 * Sync Status Widget — shows sync status for points, users, profiles, rulebooks, agents on dashboards.
 * Fetch /api/sync/status and render into an element with id="sync-status-widget" or data-sync-status-widget.
 * Optional: "Sync now" button triggers POST /api/sync/now and refreshes status.
 */
(function () {
    const API = '/api/sync/status';
    const FALLBACK = window.API_BASE ? window.API_BASE + '/sync/status' : API;
    const SYNC_NOW_API = '/api/sync/now';
    const SYNC_NOW_FALLBACK = window.API_BASE ? window.API_BASE + '/sync/now' : SYNC_NOW_API;

    function formatTime(iso) {
        if (!iso) return '—';
        try {
            const d = new Date(iso);
            return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
        } catch (e) {
            return iso;
        }
    }

    function render(container, data) {
        if (!container) return;
        const up = data.unified_points || {};
        const users = data.users || {};
        const profiles = data.profiles || {};
        const rulebooks = data.rulebooks || {};
        const agents = data.agent_skillsets || {};
        const knowledge = data.agent_knowledge || {};
        const html = `
            <div class="sync-status-widget" aria-label="Sync status">
                <div class="sync-status-header">
                    <span class="sync-status-title">Sync status</span>
                    <span class="sync-status-time">${formatTime(up.last_sync_at || data.unified_points?.last_sync_at)}</span>
                    <button type="button" class="sync-status-btn" id="sync-now-btn" aria-label="Run sync now">Sync now</button>
                </div>
                <div class="sync-status-grid">
                    <div class="sync-status-item">
                        <span class="sync-status-label">Points</span>
                        <span class="sync-status-value">${up.sync_count != null ? up.sync_count : '—'}</span>
                    </div>
                    <div class="sync-status-item">
                        <span class="sync-status-label">Users</span>
                        <span class="sync-status-value">${users.count != null ? users.count : '—'}</span>
                    </div>
                    <div class="sync-status-item">
                        <span class="sync-status-label">Profiles</span>
                        <span class="sync-status-value">${profiles.count != null ? profiles.count : '—'}</span>
                    </div>
                    <div class="sync-status-item">
                        <span class="sync-status-label">Rulebooks</span>
                        <span class="sync-status-value">${rulebooks.version || '—'}</span>
                    </div>
                    <div class="sync-status-item">
                        <span class="sync-status-label">Agents</span>
                        <span class="sync-status-value">${agents.agents_count != null ? agents.agents_count : '—'}</span>
                    </div>
                    <div class="sync-status-item">
                        <span class="sync-status-label">Knowledge</span>
                        <span class="sync-status-value">${knowledge.entries_count != null ? knowledge.entries_count : '—'}</span>
                    </div>
                </div>
            </div>
        `;
        container.innerHTML = html;
        var btn = document.getElementById('sync-now-btn');
        if (btn) {
            btn.addEventListener('click', function () {
                btn.disabled = true;
                btn.textContent = 'Syncing…';
                fetch(SYNC_NOW_FALLBACK, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
                    .then(function (r) { return r.json(); })
                    .then(function () { load(); })
                    .catch(function () { load(); })
                    .finally(function () {
                        if (btn) { btn.disabled = false; btn.textContent = 'Sync now'; }
                    });
            });
        }
    }

    function load() {
        const container = document.getElementById('sync-status-widget') || document.querySelector('[data-sync-status-widget]');
        if (!container) return;
        fetch(FALLBACK)
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.success) render(container, data);
            })
            .catch(function () {
                if (container) container.innerHTML = '<div class="sync-status-widget"><span class="sync-status-time">Sync status unavailable</span></div>';
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', load);
    } else {
        load();
    }
    window.SyncStatusWidget = { load: load };
})();
