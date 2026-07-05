/**
 * Renders Top 15 aggregator ideas from /data/aggregator_ideas_top15.json
 * into elements matching [data-aggregator-ideas="list"]
 */
(function () {
  'use strict';

  function render(container, items) {
    if (!container || !items || !items.length) return;
    var ol = document.createElement('ol');
    ol.className = 'aggregator-ideas-ol';
    ol.style.cssText =
      'margin:0;padding-left:1.2rem;line-height:1.45;font-size:0.88rem;color:var(--text-secondary,#bbb);';
    items.forEach(function (it) {
      var li = document.createElement('li');
      li.style.marginBottom = '10px';
      li.innerHTML =
        '<strong style="color:var(--primary,#00ff88);">' +
        (it.title || '') +
        '</strong> ' +
        '<span style="opacity:0.85;font-size:0.8rem;">[' +
        (it.tech || '') +
        ']</span><br><span style="opacity:0.95;">' +
        (it.blurb || '') +
        '</span>';
      ol.appendChild(li);
    });
    container.appendChild(ol);
    if (window.location.pathname.indexOf('/aggregator') === -1) {
      var link = document.createElement('p');
      link.style.marginTop = '12px';
      link.innerHTML =
        '<a href="/aggregator" style="color:var(--secondary,#6cf);font-weight:600;">Open aggregator hub →</a>';
      container.appendChild(link);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var nodes = document.querySelectorAll('[data-aggregator-ideas="list"]');
    if (!nodes.length) return;
    fetch('/static/data/aggregator_ideas_top15.json')
      .then(function (r) {
        return r.json();
      })
      .then(function (data) {
        nodes.forEach(function (el) {
          el.innerHTML = '';
          render(el, data);
        });
      })
      .catch(function () {
        nodes.forEach(function (el) {
          el.innerHTML = '<p style="color:#f88;">Could not load idea list.</p>';
        });
      });
  });
})();
