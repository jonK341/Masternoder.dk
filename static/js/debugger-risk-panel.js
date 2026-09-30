/**
 * Debugger fraud & risk panel — GET /api/admin/risk/*
 */
(function () {
    'use strict';

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function key() {
        var el = document.getElementById('risk-admin-key');
        return el ? (el.value || '').trim() : '';
    }

    function headers() {
        return { 'X-Cogs-Admin-Key': key() };
    }

    function renderSummary(data) {
        var el = document.getElementById('risk-summary-out');
        if (!el) return;
        if (!data || !data.success) {
            el.innerHTML = '<p class="dim">' + esc((data && data.error) || 'No summary') + '</p>';
            return;
        }
        el.innerHTML =
            '<p><strong>Total logged:</strong> ' + esc(data.total_logged) + '</p>' +
            '<p><strong>24h levels:</strong> ' + esc(JSON.stringify(data.by_level_24h || {})) + '</p>' +
            '<p><strong>7d levels:</strong> ' + esc(JSON.stringify(data.by_level_7d || {})) + '</p>' +
            '<p><strong>High-risk users (recent):</strong> ' + esc((data.recent_high_users || []).join(', ') || '—') + '</p>';
    }

    function renderWithdrawals(data) {
        var el = document.getElementById('risk-withdrawals-out');
        if (!el) return;
        if (!data || !data.success) {
            el.innerHTML = '<p class="dim">' + esc((data && data.error) || 'Failed') + '</p>';
            return;
        }
        var rows = data.assessments || [];
        if (!rows.length) {
            el.innerHTML = '<p class="dim">No withdrawal assessments logged yet.</p>';
            return;
        }
        var html = '<table style="width:100%;border-collapse:collapse;font-size:12px;"><thead><tr>' +
            '<th style="text-align:left;padding:6px;">Time</th><th>User</th><th>Level</th><th>Score</th><th>Reasons</th></tr></thead><tbody>';
        rows.forEach(function (r) {
            var lvl = (r.level || '').toLowerCase();
            var color = lvl === 'high' ? '#ff8a80' : lvl === 'elevated' ? '#ffd54f' : '#a5d6a7';
            html += '<tr style="border-top:1px solid rgba(255,255,255,0.08);">' +
                '<td style="padding:6px;">' + esc((r.ts || '').slice(0, 19)) + '</td>' +
                '<td style="padding:6px;">' + esc(r.user_id) + '</td>' +
                '<td style="padding:6px;color:' + color + ';">' + esc(r.level) + '</td>' +
                '<td style="padding:6px;">' + esc(r.score) + '</td>' +
                '<td style="padding:6px;">' + esc((r.reasons || []).join('; ')) + '</td></tr>';
        });
        html += '</tbody></table>';
        el.innerHTML = html;
    }

    function renderSybil(data) {
        var el = document.getElementById('risk-sybil-out');
        if (!el) return;
        if (!data || !data.success) {
            el.innerHTML = '<p class="dim">' + esc((data && data.error) || 'Failed') + '</p>';
            return;
        }
        var clusters = data.clusters || [];
        if (!clusters.length) {
            el.innerHTML = '<p class="dim">No elevated sybil clusters.</p>';
            return;
        }
        var html = '<ul style="margin:0;padding-left:18px;">';
        clusters.forEach(function (c) {
            html += '<li style="margin-bottom:8px;"><strong>' + esc(c.user_id) + '</strong> — score ' +
                esc(c.sybil_score) + ', cluster ' + esc(c.cluster_size) +
                ' <span class="dim">(' + esc((c.cluster_users || []).join(', ')) + ')</span></li>';
        });
        html += '</ul>';
        el.innerHTML = html;
    }

    window.loadFraudRiskPanel = function () {
        var k = key();
        if (!k) {
            ['risk-summary-out', 'risk-withdrawals-out', 'risk-sybil-out'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.innerHTML = '<p class="dim">Enter COGS admin key above.</p>';
            });
            return Promise.resolve();
        }
        return Promise.all([
            fetch('/api/admin/risk/summary?key=' + encodeURIComponent(k), { headers: headers() }).then(function (r) { return r.json(); }),
            fetch('/api/admin/risk/withdrawals?limit=80&key=' + encodeURIComponent(k), { headers: headers() }).then(function (r) { return r.json(); }),
            fetch('/api/admin/risk/sybil?limit=30&key=' + encodeURIComponent(k), { headers: headers() }).then(function (r) { return r.json(); }),
        ]).then(function (parts) {
            renderSummary(parts[0]);
            renderWithdrawals(parts[1]);
            renderSybil(parts[2]);
        }).catch(function () {
            ['risk-summary-out', 'risk-withdrawals-out', 'risk-sybil-out'].forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.innerHTML = '<p class="dim">Request failed.</p>';
            });
        });
    };
})();
