/**
 * MN2 tip strip for chat — balance, presets, POST /api/chat/tip
 */
(function (global) {
    'use strict';

    var bridge = global.Mn2SiteBridge;

    function uid() {
        return bridge ? bridge.uid() : (global.localStorage.getItem('game_user_id') || 'default_user');
    }

    function fmt(n) {
        return bridge ? bridge.fmtMn2(n) : String(n);
    }

    function setText(id, text) {
        var el = global.document.getElementById(id);
        if (el) el.textContent = text;
    }

    function showStatus(msg, ok) {
        var el = global.document.getElementById('chat-tip-status');
        if (!el) return;
        el.textContent = msg;
        el.style.color = ok ? '#00ff88' : '#ff8888';
    }

    function refreshBalance() {
        if (!bridge) return Promise.resolve();
        return bridge.loadBalance().then(function (d) {
            var bal = (d && (d.balance != null ? d.balance : d.mn2_balance)) || 0;
            setText('chat-mn2-balance', fmt(bal) + ' MN2');
        }).catch(function () {
            setText('chat-mn2-balance', '—');
        });
    }

    function loadConfig() {
        return fetch('/api/chat/tip/config').then(function (r) { return r.json(); }).then(function (d) {
            if (!d.success) return;
            var wrap = global.document.getElementById('chat-tip-presets');
            if (!wrap) return;
            wrap.innerHTML = (d.presets || []).map(function (amt) {
                return '<button type="button" class="chat-tip-preset" data-amt="' + amt + '">' + fmt(amt) + ' MN2</button>';
            }).join('');
            wrap.querySelectorAll('.chat-tip-preset').forEach(function (btn) {
                btn.addEventListener('click', function () {
                    var input = global.document.getElementById('chat-tip-amount');
                    if (input) input.value = btn.getAttribute('data-amt');
                });
            });
        }).catch(function () { /* ignore */ });
    }

    function sendTip() {
        var toInput = global.document.getElementById('chat-tip-recipient');
        var amtInput = global.document.getElementById('chat-tip-amount');
        var msgInput = global.document.getElementById('chat-tip-message');
        var btn = global.document.getElementById('chat-tip-send');
        var toUser = (toInput && toInput.value || '').trim();
        var amount = parseFloat(amtInput && amtInput.value);
        var message = (msgInput && msgInput.value || '').trim();
        if (!toUser) {
            showStatus('Enter a recipient user id', false);
            return;
        }
        if (!isFinite(amount) || amount <= 0) {
            showStatus('Enter a valid tip amount', false);
            return;
        }
        if (btn) { btn.disabled = true; btn.textContent = 'Sending…'; }
        showStatus('', true);
        fetch('/api/chat/tip', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: uid(),
                to_user_id: toUser,
                amount: amount,
                message: message,
            }),
        }).then(function (r) { return r.json(); }).then(function (d) {
            if (d.success) {
                showStatus('Sent ' + fmt(d.amount) + ' MN2 to ' + d.to_user_id, true);
                if (amtInput) amtInput.value = '';
                if (msgInput) msgInput.value = '';
                refreshBalance();
            } else {
                showStatus(d.error || 'Tip failed', false);
            }
        }).catch(function () {
            showStatus('Network error sending tip', false);
        }).finally(function () {
            if (btn) { btn.disabled = false; btn.textContent = 'Send tip'; }
        });
    }

    function init() {
        refreshBalance();
        loadConfig();
        bridge && bridge.loadPrice().then(function (d) {
            var p = d && (d.price_usd != null ? d.price_usd : d.usd);
            setText('chat-mn2-rate', p != null ? ('$' + Number(p).toFixed(4) + ' / MN2') : '—');
        }).catch(function () { setText('chat-mn2-rate', '—'); });
        var btn = global.document.getElementById('chat-tip-send');
        if (btn) btn.addEventListener('click', sendTip);
    }

    global.ChatMn2Tips = { init: init, refreshBalance: refreshBalance, sendTip: sendTip };
    global.document.addEventListener('DOMContentLoaded', init);
})(window);
