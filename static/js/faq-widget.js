/**
 * Floating FAQ widget — POST /api/support/faq/ask (free-tier LLM + keyword fallback).
 */
(function () {
    'use strict';

    function uid() {
        try {
            return localStorage.getItem('game_user_id') || localStorage.getItem('user_id') || 'default_user';
        } catch (e) {
            return 'default_user';
        }
    }

    function esc(s) {
        var d = document.createElement('div');
        d.textContent = s == null ? '' : String(s);
        return d.innerHTML;
    }

    function ensureStyles() {
        if (document.getElementById('mn-faq-widget-css')) return;
        var link = document.createElement('link');
        link.id = 'mn-faq-widget-css';
        link.rel = 'stylesheet';
        link.href = '/static/css/ai-assist-widgets.css?v=20260624';
        document.head.appendChild(link);
    }

    function addMsg(container, text, role) {
        var el = document.createElement('div');
        el.className = 'mn-assist-msg ' + (role || 'bot');
        el.textContent = text;
        container.appendChild(el);
        container.scrollTop = container.scrollHeight;
    }

    function ask(question, msgsEl, topicsEl) {
        addMsg(msgsEl, question, 'user');
        fetch('/api/support/faq/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question, channel: 'web', user_id: uid() }),
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                addMsg(msgsEl, data.answer || 'No answer available.', 'bot');
                if (topicsEl && data.topics && data.topics.length) {
                    topicsEl.innerHTML = '';
                    data.topics.slice(0, 10).forEach(function (t) {
                        var b = document.createElement('button');
                        b.type = 'button';
                        b.textContent = t;
                        b.addEventListener('click', function () {
                            ask(t, msgsEl, topicsEl);
                        });
                        topicsEl.appendChild(b);
                    });
                }
            })
            .catch(function () {
                addMsg(msgsEl, 'Could not reach support API. Try Profile or /shop/ for help.', 'bot');
            });
    }

    function mount() {
        if (document.getElementById('mn-faq-launcher')) return;
        ensureStyles();

        var panel = document.createElement('div');
        panel.id = 'mn-faq-panel';
        panel.className = 'mn-assist-panel';
        panel.innerHTML =
            '<div class="mn-assist-head"><span>Help — MN2 &amp; Shop</span><button type="button" aria-label="Close">&times;</button></div>' +
            '<div class="mn-assist-body">' +
            '<div class="mn-assist-msgs" id="mn-faq-msgs"></div>' +
            '<div class="mn-assist-input-row">' +
            '<input type="text" id="mn-faq-input" placeholder="Ask about deposit, staking, shop…" maxlength="400">' +
            '<button type="button" id="mn-faq-send">Ask</button>' +
            '</div>' +
            '<div class="mn-assist-topics" id="mn-faq-topics"></div>' +
            '</div>';

        var btn = document.createElement('button');
        btn.type = 'button';
        btn.id = 'mn-faq-launcher';
        btn.className = 'mn-faq-launcher';
        btn.textContent = '? Help';

        document.body.appendChild(panel);
        document.body.appendChild(btn);

        var msgsEl = panel.querySelector('#mn-faq-msgs');
        var topicsEl = panel.querySelector('#mn-faq-topics');
        var input = panel.querySelector('#mn-faq-input');

        panel.querySelector('.mn-assist-head button').addEventListener('click', function () {
            panel.classList.remove('open');
        });
        btn.addEventListener('click', function () {
            panel.classList.toggle('open');
            if (panel.classList.contains('open') && !msgsEl.childElementCount) {
                addMsg(msgsEl, 'Hi! Ask about MN2 wallet, staking, hosting, shop, or generator.', 'bot');
                fetch('/api/support/faq/topics')
                    .then(function (r) { return r.json(); })
                    .then(function (d) {
                        if (d.topics) {
                            topicsEl.innerHTML = '';
                            d.topics.slice(0, 10).forEach(function (t) {
                                var b = document.createElement('button');
                                b.type = 'button';
                                b.textContent = t;
                                b.addEventListener('click', function () { ask(t, msgsEl, topicsEl); });
                                topicsEl.appendChild(b);
                            });
                        }
                    });
            }
        });
        panel.querySelector('#mn-faq-send').addEventListener('click', function () {
            var q = (input.value || '').trim();
            if (!q) return;
            input.value = '';
            ask(q, msgsEl, topicsEl);
        });
        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') panel.querySelector('#mn-faq-send').click();
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mount);
    } else {
        mount();
    }

    window.MnFaqWidget = { mount: mount };
})();
