/**
 * Pro-gated copy assist — POST /api/assist/copy
 * Mount inline panels via data-copy-assist on script tag or MnCopyAssist.mountInline(...)
 */
(function () {
    'use strict';

    var SITE_PRESETS = {
        generator: {
            kinds: ['video_title', 'video_description'],
            targets: { video_title: '#videoTitle', video_description: '#videoDesc' },
        },
        shop: {
            kinds: ['product_title', 'product_description', 'shop_listing'],
            targets: {},
        },
        hosting: {
            kinds: ['product_description'],
            targets: {},
        },
    };

    function uid() {
        try {
            return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
        } catch (e) {
            return 'default_user';
        }
    }

    function ensureStyles() {
        if (document.getElementById('mn-copy-widget-css')) return;
        var link = document.createElement('link');
        link.id = 'mn-copy-widget-css';
        link.rel = 'stylesheet';
        link.href = '/static/css/ai-assist-widgets.css?v=20260624';
        document.head.appendChild(link);
    }

    function subjectFromPage() {
        var t = document.querySelector('#videoTitle, [name="title"], h1');
        return t && (t.value || t.textContent) ? String(t.value || t.textContent).trim().slice(0, 120) : '';
    }

    function buildPanel(kind, targetSelector, onApply) {
        var wrap = document.createElement('div');
        wrap.className = 'mn-copy-inline';
        wrap.innerHTML =
            '<div style="font-size:12px;font-weight:600;margin-bottom:6px;">✨ Pro Copy Assist</div>' +
            '<textarea rows="2" placeholder="Keywords or brief (optional)" class="mn-copy-keywords"></textarea>' +
            '<div style="display:flex;gap:8px;margin-top:8px;flex-wrap:wrap;">' +
            '<button type="button" class="mn-copy-gen">Generate</button>' +
            '<button type="button" class="mn-copy-apply" disabled style="background:#455a64;color:#fff;">Use text</button>' +
            '</div>' +
            '<div class="mn-copy-result" style="display:none;"></div>' +
            '<div class="mn-copy-upsell" style="display:none;"></div>';

        var resultEl = wrap.querySelector('.mn-copy-result');
        var upsellEl = wrap.querySelector('.mn-copy-upsell');
        var applyBtn = wrap.querySelector('.mn-copy-apply');
        var lastText = '';

        wrap.querySelector('.mn-copy-gen').addEventListener('click', function () {
            resultEl.style.display = 'none';
            upsellEl.style.display = 'none';
            applyBtn.disabled = true;
            resultEl.textContent = 'Generating…';
            resultEl.style.display = 'block';
            fetch('/api/assist/copy', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: uid(),
                    kind: kind,
                    context: {
                        subject: subjectFromPage(),
                        keywords: (wrap.querySelector('.mn-copy-keywords').value || '').trim(),
                    },
                }),
            })
                .then(function (r) { return r.json().then(function (d) { return { status: r.status, data: d }; }); })
                .then(function (res) {
                    var d = res.data;
                    if (!d.success) {
                        resultEl.textContent = d.message || d.error || 'Copy assist unavailable.';
                        if (d.upsell) {
                            upsellEl.style.display = 'block';
                            upsellEl.innerHTML = (d.upsell.message || 'Upgrade to Pro') +
                                ' <a href="/shop/" style="color:#80cbc4;">Shop →</a>';
                        }
                        return;
                    }
                    lastText = d.text || '';
                    resultEl.textContent = lastText;
                    applyBtn.disabled = !lastText;
                })
                .catch(function () {
                    resultEl.textContent = 'Request failed.';
                });
        });

        applyBtn.addEventListener('click', function () {
            if (!lastText) return;
            if (targetSelector) {
                var el = document.querySelector(targetSelector);
                if (el) {
                    if ('value' in el) el.value = lastText;
                    else el.textContent = lastText;
                }
            }
            if (typeof onApply === 'function') onApply(lastText);
        });

        return wrap;
    }

    function mountForSite(site) {
        ensureStyles();
        var preset = SITE_PRESETS[site] || SITE_PRESETS.shop;
        preset.kinds.forEach(function (kind) {
            var anchor = document.querySelector('[data-copy-anchor="' + kind + '"]');
            if (!anchor) {
                var sel = preset.targets[kind];
                if (sel) anchor = document.querySelector(sel);
                if (anchor && anchor.parentElement) anchor = anchor.parentElement;
            }
            if (!anchor || anchor.querySelector('.mn-copy-inline')) return;
            anchor.appendChild(buildPanel(kind, preset.targets[kind] || null));
        });
    }

    function initFromScriptTag() {
        var scripts = document.querySelectorAll('script[data-copy-assist]');
        scripts.forEach(function (s) {
            mountForSite(s.getAttribute('data-copy-assist') || 'shop');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initFromScriptTag);
    } else {
        initFromScriptTag();
    }

    window.MnCopyAssist = { mountForSite: mountForSite, buildPanel: buildPanel };
})();
