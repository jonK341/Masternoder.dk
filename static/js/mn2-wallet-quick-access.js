/**
 * MN2 Wallet Quick Access — site-wide chip, FAB, sticky bar, keyboard shortcut.
 * Depends on mn2-site-bridge.js for user_id sync and balance API.
 */
(function (global) {
    'use strict';

    var CACHE_VER = '20260910a';
    var REFRESH_MS = 90000;
    var _balance = null;
    var _dropdownOpen = false;
    var _dropdownEl = null;

    var QUICK_ACTIONS = [
        { icon: '👛', label: 'Open wallet', href: '/wallets' },
        { icon: '📥', label: 'Deposit', href: '/profile?tab=wallet&wallet=deposit' },
        { icon: '📤', label: 'Withdraw', href: '/profile?tab=wallet&wallet=withdraw' },
        { icon: '🛒', label: 'Shop', href: '/shop#shop-mn2' },
        { icon: '💱', label: 'Exchange', href: '/exchange' },
        { icon: '🌱', label: 'Staking', href: '/profile?tab=wallet' },
    ];

    var STICKY_PATHS = ['/shop', '/casino', '/exchange'];

    function bridge() {
        return global.Mn2SiteBridge || null;
    }

    function fmt(n) {
        var b = bridge();
        if (b && b.fmtMn2) return b.fmtMn2(n);
        var v = parseFloat(n);
        if (!isFinite(v)) return '0';
        return v.toLocaleString(undefined, { maximumFractionDigits: 4 });
    }

    function uid() {
        var b = bridge();
        if (b && b.uid) return b.uid();
        try {
            var game = global.localStorage.getItem('game_user_id');
            var user = global.localStorage.getItem('user_id');
            if (game && game !== 'default_user') return game;
            if (user && user !== 'default_user') return user;
        } catch (e) { /* ignore */ }
        return 'default_user';
    }

    function isAnonymous() {
        return uid() === 'default_user';
    }

    function isTypingTarget(el) {
        if (!el || !el.tagName) return false;
        var tag = el.tagName.toLowerCase();
        return tag === 'input' || tag === 'textarea' || tag === 'select' || el.isContentEditable;
    }

    function setBalanceText(text) {
        var ids = ['navToolbarMn2Balance', 'mn2WalletFabBalance', 'mn2StickyBarBalance'];
        ids.forEach(function (id) {
            var el = global.document.getElementById(id);
            if (el) el.textContent = text;
        });
    }

    function closeDropdown() {
        if (_dropdownEl) {
            _dropdownEl.remove();
            _dropdownEl = null;
        }
        _dropdownOpen = false;
        var chip = global.document.getElementById('navToolbarMn2Wallet');
        if (chip) chip.classList.remove('is-open');
    }

    function openDropdown(anchor) {
        closeDropdown();
        if (!anchor) return;

        var rect = anchor.getBoundingClientRect();
        var dd = global.document.createElement('div');
        dd.className = 'mn2-wallet-dropdown';
        dd.setAttribute('role', 'menu');
        dd.innerHTML =
            '<div class="mn2-wallet-dropdown-header">' +
                'MN2 Wallet' +
                '<span class="mn2-wallet-dropdown-balance">' + (isAnonymous() ? 'Sign in to view' : fmt(_balance) + ' MN2') + '</span>' +
            '</div>' +
            QUICK_ACTIONS.map(function (a) {
                return '<a class="mn2-wallet-dropdown-item" role="menuitem" href="' + a.href + '">' +
                    '<span>' + a.icon + '</span>' + a.label + '</a>';
            }).join('') +
            '<div class="mn2-wallet-dropdown-hint">Press <kbd>W</kbd> anytime · tap chip to toggle</div>';

        dd.style.top = (rect.bottom + 6) + 'px';
        dd.style.right = Math.max(8, global.window.innerWidth - rect.right) + 'px';

        global.document.body.appendChild(dd);
        _dropdownEl = dd;
        _dropdownOpen = true;
        anchor.classList.add('is-open');

        setTimeout(function () {
            global.document.addEventListener('click', onOutsideClick);
            global.document.addEventListener('keydown', onEscClose);
        }, 0);
    }

    function onOutsideClick(e) {
        var chip = global.document.getElementById('navToolbarMn2Wallet');
        if (_dropdownEl && !_dropdownEl.contains(e.target) && chip && !chip.contains(e.target)) {
            closeDropdown();
            global.document.removeEventListener('click', onOutsideClick);
            global.document.removeEventListener('keydown', onEscClose);
        }
    }

    function onEscClose(e) {
        if (e.key === 'Escape') {
            closeDropdown();
            global.document.removeEventListener('click', onOutsideClick);
            global.document.removeEventListener('keydown', onEscClose);
        }
    }

    function toggleDropdown(e) {
        if (e) {
            e.preventDefault();
            e.stopPropagation();
        }
        var chip = global.document.getElementById('navToolbarMn2Wallet');
        if (!chip) return;
        if (_dropdownOpen) closeDropdown();
        else openDropdown(chip);
    }

    function goWallet(e) {
        if (e) e.preventDefault();
        global.location.href = isAnonymous() ? '/profile?tab=wallet' : '/wallets';
    }

    function bindChip() {
        var chip = global.document.getElementById('navToolbarMn2Wallet');
        if (!chip || chip.dataset.mn2Bound) return;
        chip.dataset.mn2Bound = '1';

        chip.addEventListener('click', function (e) {
            if (e.target.closest('.nav-toolbar-mn2-chevron') || e.detail === 1) {
                toggleDropdown(e);
            }
        });
        chip.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleDropdown(e);
            }
        });
        chip.addEventListener('dblclick', function (e) {
            e.preventDefault();
            goWallet();
        });
    }

    function injectFab() {
        if (global.document.getElementById('mn2WalletFab')) return;
        var fab = global.document.createElement('a');
        fab.id = 'mn2WalletFab';
        fab.className = 'mn2-wallet-fab';
        fab.href = '/wallets';
        fab.title = 'MN2 Wallet (W)';
        fab.setAttribute('aria-label', 'Open MN2 wallet');
        fab.innerHTML =
            '<span class="mn2-wallet-fab-icon">⚡</span>' +
            '<span class="mn2-wallet-fab-balance" id="mn2WalletFabBalance">—</span>';
        fab.addEventListener('click', function (e) {
            if (isAnonymous()) {
                e.preventDefault();
                global.location.href = '/profile?tab=wallet';
            }
        });
        global.document.body.appendChild(fab);
    }

    function onStickyPath() {
        var path = (global.location.pathname || '').replace(/\/$/, '') || '/';
        return STICKY_PATHS.some(function (p) {
            return path === p || path.indexOf(p + '/') === 0;
        });
    }

    function injectStickyBar() {
        if (!onStickyPath() || global.document.getElementById('mn2WalletStickyBar')) return;

        global.document.body.classList.add('mn2-wallet-sticky-active');
        var bar = global.document.createElement('div');
        bar.id = 'mn2WalletStickyBar';
        bar.className = 'mn2-wallet-sticky-bar';
        bar.innerHTML =
            '<div class="mn2-wallet-sticky-bar-left">' +
                '<span class="mn2-wallet-sticky-bar-label">MN2</span>' +
                '<strong id="mn2StickyBarBalance">—</strong>' +
            '</div>' +
            '<div class="mn2-wallet-sticky-actions">' +
                '<a class="mn2-wallet-sticky-btn" href="/profile?tab=wallet&wallet=deposit">Deposit</a>' +
                '<a class="mn2-wallet-sticky-btn mn2-wallet-sticky-btn--primary" href="/wallets">Wallet</a>' +
            '</div>';
        global.document.body.appendChild(bar);
    }

    function enhanceHeroTicker() {
        var ticker = global.document.querySelector('.fp-ticker-balance');
        if (!ticker || ticker.dataset.mn2Enhanced) return;
        ticker.dataset.mn2Enhanced = '1';
        ticker.classList.add('is-clickable');
        ticker.setAttribute('role', 'button');
        ticker.setAttribute('tabindex', '0');
        ticker.setAttribute('title', 'Open MN2 wallet');
        ticker.addEventListener('click', goWallet);
        ticker.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                goWallet();
            }
        });
    }

    function bindKeyboard() {
        if (global.document.body.dataset.mn2WalletKeyBound) return;
        global.document.body.dataset.mn2WalletKeyBound = '1';
        global.document.addEventListener('keydown', function (e) {
            if (e.defaultPrevented || e.metaKey || e.ctrlKey || e.altKey) return;
            if (isTypingTarget(e.target)) return;
            if (e.key === 'w' || e.key === 'W') {
                e.preventDefault();
                goWallet();
            }
        });
    }

    function loadBalance() {
        var chip = global.document.getElementById('navToolbarMn2Wallet');
        if (chip) chip.classList.add('is-loading');

        if (isAnonymous()) {
            _balance = null;
            setBalanceText('Sign in');
            if (chip) {
                chip.classList.remove('is-loading');
                chip.classList.add('is-anonymous');
            }
            return Promise.resolve(null);
        }

        var loader = bridge() ? bridge().loadBalance() : fetch('/api/mn2/balance?user_id=' + encodeURIComponent(uid())).then(function (r) {
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return r.json();
        });

        return loader.then(function (d) {
            var bal = (d && (d.mn2_balance != null ? d.mn2_balance : d.balance)) || 0;
            _balance = bal;
            var text = fmt(bal);
            setBalanceText(text);
            if (chip) {
                chip.classList.remove('is-loading', 'is-anonymous');
            }
            return bal;
        }).catch(function () {
            setBalanceText('—');
            if (chip) chip.classList.remove('is-loading');
            return null;
        });
    }

    function loadCss() {
        if (global.document.querySelector('link[href*="mn2-wallet-quick-access.css"]')) return;
        var link = global.document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/css/mn2-wallet-quick-access.css?v=' + CACHE_VER;
        global.document.head.appendChild(link);
    }

    function init() {
        loadCss();
        bindChip();
        injectFab();
        injectStickyBar();
        enhanceHeroTicker();
        bindKeyboard();
        loadBalance();
        setInterval(loadBalance, REFRESH_MS);
    }

    function waitForBridge(cb) {
        if (bridge()) {
            cb();
            return;
        }
        var attempts = 0;
        var t = setInterval(function () {
            attempts++;
            if (bridge() || attempts > 40) {
                clearInterval(t);
                cb();
            }
        }, 100);
    }

    function boot() {
        waitForBridge(init);
    }

    if (global.document.readyState === 'loading') {
        global.document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }

    global.Mn2WalletQuickAccess = {
        refresh: loadBalance,
        goWallet: goWallet,
        getBalance: function () { return _balance; },
        uid: uid,
    };
})(window);
