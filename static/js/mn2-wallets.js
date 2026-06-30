/**
 * MN2 Wallets download page — renders release catalog from GET /api/mn2/releases
 */
(function () {
  'use strict';

  function el(id) {
    return document.getElementById(id);
  }

  function fmtBytes(n) {
    if (n == null || !isFinite(n)) return '';
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1048576).toFixed(1) + ' MB';
  }

  function renderCard(item, featured) {
    var tags = (item.recommended_for || [])
      .map(function (t) {
        return '<span class="mn2-wallet-dl-tag">' + t + '</span>';
      })
      .join('');
    var checksum = item.sha256
      ? '<div class="mn2-wallet-dl-checksum" title="Verify after download">SHA256<br>' + item.sha256 + '</div>'
      : '';
    var tagNote = item.release_tag
      ? '<p class="mn2-wallet-dl-tag-note" style="font-size:0.75rem;opacity:0.75;margin:8px 0 0;">Release: ' + item.release_tag + '</p>'
      : '';
    var copyBtn = item.sha256
      ? '<button type="button" class="mn2-wallet-dl-btn mn2-wallet-dl-btn--ghost" data-copy-sha="' +
        item.sha256 +
        '">Copy checksum</button>'
      : '';
    return (
      '<article class="mn2-wallet-dl-card' +
      (featured ? ' mn2-wallet-dl-card--featured' : '') +
      '">' +
      '<div class="mn2-wallet-dl-head">' +
      '<span class="mn2-wallet-dl-icon" aria-hidden="true">' +
      (item.icon || '💠') +
      '</span>' +
      '<div><h3 class="mn2-wallet-dl-title">' +
      item.name +
      '</h3>' +
      '<p class="mn2-wallet-dl-platform">' +
      item.platform +
      ' · ' +
      (item.format || '').toUpperCase() +
      '</p></div></div>' +
      '<p class="mn2-wallet-dl-desc">' +
      (item.description || '') +
      '</p>' +
      tagNote +
      '<div class="mn2-wallet-dl-tags">' +
      tags +
      '</div>' +
      '<div class="mn2-wallet-dl-actions">' +
      '<a class="mn2-wallet-dl-btn" href="' +
      item.url +
      '" download rel="noopener">' +
      '<i class="fas fa-download"></i> Download ' +
      item.filename +
      '</a>' +
      '<a class="mn2-wallet-dl-btn mn2-wallet-dl-btn--ghost" href="' +
      item.url +
      '" target="_blank" rel="noopener">Open link</a>' +
      copyBtn +
      '</div>' +
      checksum +
      '</article>'
    );
  }

  function wireCopy() {
    document.querySelectorAll('[data-copy-sha]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var sha = btn.getAttribute('data-copy-sha');
        if (navigator.clipboard && sha) {
          navigator.clipboard.writeText(sha).then(function () {
            btn.textContent = 'Copied!';
            setTimeout(function () {
              btn.textContent = 'Copy checksum';
            }, 1500);
          });
        }
      });
    });
  }

  function loadPeers() {
    var box = el('mn2-wallets-peers');
    var copyBtn = el('mn2-wallets-copy-conf');
    if (!box) return;

    fetch('/api/mn2/network-peers', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.success || !d.mainnet) {
          box.innerHTML = '<p style="opacity:0.8;">Peer list unavailable.</p>';
          return;
        }
        var peers = d.mainnet.addnodes || [];
        var html =
          '<p><strong>Recommended addnode= lines</strong> (append to masternoder2.conf):</p>' +
          '<pre class="mn2-wallets-peer-pre">' +
          peers.map(function (p) {
            return 'addnode=' + p;
          }).join('\n') +
          '</pre>';
        box.innerHTML = html;
        if (copyBtn && d.conf_snippet_mainnet) {
          copyBtn.style.display = 'inline-block';
          copyBtn.onclick = function () {
            if (navigator.clipboard) {
              navigator.clipboard.writeText(d.conf_snippet_mainnet).then(function () {
                copyBtn.textContent = 'Copied!';
                setTimeout(function () {
                  copyBtn.textContent = 'Copy bootstrap conf snippet';
                }, 1500);
              });
            }
          };
        }
      })
      .catch(function () {
        box.innerHTML = '<p style="opacity:0.8;">Could not load peer list.</p>';
      });
  }

  function load() {
    var grid = el('mn2-wallets-grid');
    var versionEl = el('mn2-wallets-version');
    var ghEl = el('mn2-wallets-github');
    if (!grid) return;

    fetch('/api/mn2/releases', { credentials: 'same-origin' })
      .then(function (r) {
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.success) {
          grid.innerHTML = '<p style="opacity:0.8;">Could not load release catalog.</p>';
          return;
        }
        if (versionEl) versionEl.textContent = d.version || '—';
        if (ghEl && d.github_releases) {
          ghEl.href = d.github_releases;
        }
        var items = d.downloads || [];
        grid.innerHTML = items
          .map(function (item, i) {
            return renderCard(item, i === 0);
          })
          .join('');
        wireCopy();
      })
      .catch(function () {
        grid.innerHTML = '<p style="opacity:0.8;">Release catalog unavailable — try again shortly.</p>';
      });
  }

  function loadNetworkStrip() {
    var box = el('mn2-wallets-network');
    if (!box) return;
    fetch('/api/mn2/network-dashboard', { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d || !d.success) {
          box.textContent = 'Network status unavailable.';
          return;
        }
        var net = d.network || {};
        var sp = d.spork_gates || {};
        var mn = d.masternodes || {};
        var parts = [];
        if (net.block_height != null) parts.push('Height ' + net.block_height);
        if (net.connections != null) parts.push(net.connections + ' daemon peers');
        if (net.peer_catalog_count) parts.push(net.peer_catalog_count + ' bootstrap nodes');
        if (mn.enabled != null) parts.push(mn.enabled + ' masternodes live');
        if (sp.maintenance_mode) parts.push('Maintenance mode');
        box.textContent = parts.length ? parts.join(' · ') : 'Network data loading…';
      })
      .catch(function () { box.textContent = 'Could not load network status.'; });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      load();
      loadPeers();
      loadNetworkStrip();
    });
  } else {
    load();
    loadPeers();
    loadNetworkStrip();
  }
})();
