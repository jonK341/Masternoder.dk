/**
 * Player profiler — saved pictures + camgirl studio portrait board on profile page.
 */
(function (global) {
  'use strict';

  function apiBase() {
    if (global.APP_BASE) return String(global.APP_BASE);
    var path = global.location && global.location.pathname ? global.location.pathname : '';
    return path.indexOf('/vidgenerator/') === 0 ? '/vidgenerator' : '';
  }

  function userId() {
    if (global.MnUserId && typeof global.MnUserId.read === 'function') {
      return global.MnUserId.read();
    }
    try {
      return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || '';
    } catch (e) {
      return '';
    }
  }

  function esc(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function renderGrid(host, items, emptyText) {
    if (!host) return;
    if (!items || !items.length) {
      host.innerHTML = '<p style="opacity:0.8;font-size:0.9rem;">' + esc(emptyText) + '</p>';
      return;
    }
    host.innerHTML = items
      .map(function (row) {
        var url = row.url || row.picture_url || '';
        var label = row.display_name || row.source || 'Picture';
        return (
          '<figure class="profiler-pic-card">' +
          '<img src="' +
          esc(url) +
          '" alt="' +
          esc(label) +
          '" loading="lazy">' +
          '<figcaption>' +
          esc(label) +
          '</figcaption>' +
          '<button type="button" class="profiler-use-avatar" data-url="' +
          esc(url) +
          '">Use as profiler avatar</button>' +
          '</figure>'
        );
      })
      .join('');
    host.querySelectorAll('.profiler-use-avatar').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var url = btn.getAttribute('data-url');
        fetch(apiBase() + '/api/profiler/pictures/avatar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId(), url: url }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (data) {
            var status = document.getElementById('profiler-pictures-status');
            if (status) {
              status.textContent = data.success
                ? 'Profiler avatar updated.'
                : data.error || 'Could not save avatar.';
            }
          });
      });
    });
  }

  function boot() {
    var uid = userId();
    var savedHost = document.getElementById('profiler-pictures-saved');
    var studioHost = document.getElementById('profiler-pictures-studio');
    if (!savedHost && !studioHost) return;
    fetch(apiBase() + '/api/profiler/pictures?user_id=' + encodeURIComponent(uid || 'default_user'))
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data.success) return;
        var saved = (data.picture_gallery || []).map(function (row) {
          return { url: row.url, source: row.source || 'saved' };
        });
        renderGrid(savedHost, saved, 'Unlock camgirl rooms or save a URL below.');
        renderGrid(
          studioHost,
          data.camgirl_pictures || [],
          'Unlock a performer to show studio portraits here.'
        );
        var hero = document.getElementById('profiler-pictures-hero');
        if (hero && data.avatar_url) {
          hero.src = data.avatar_url;
        }
      })
      .catch(function () {});

    var saveBtn = document.getElementById('profiler-pictures-save-btn');
    var urlInput = document.getElementById('profiler-pictures-url');
    if (saveBtn && urlInput) {
      saveBtn.addEventListener('click', function () {
        var url = (urlInput.value || '').trim();
        if (!url) return;
        fetch(apiBase() + '/api/profiler/pictures', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: userId(), url: url, source: 'profile_manual' }),
        })
          .then(function (res) {
            return res.json();
          })
          .then(function (data) {
            var status = document.getElementById('profiler-pictures-status');
            if (status) {
              status.textContent = data.success ? 'Picture saved to profiler.' : data.error || 'Save failed.';
            }
            if (data.success) boot();
          });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})(window);
