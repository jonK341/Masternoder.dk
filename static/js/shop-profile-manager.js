/**
 * Shop profile manager.
 * Uses the same account id and profile APIs as /profile so checkout, inventory,
 * and the profile form stay on one game_user_id.
 */
(function () {
    var prefsCache = {};

    function uidStored() {
        return localStorage.getItem('game_user_id') || 'default_user';
    }

    function asObject(value) {
        if (value && typeof value === 'object') return value;
        if (typeof value === 'string') {
            try {
                var parsed = JSON.parse(value);
                if (parsed && typeof parsed === 'object') return parsed;
            } catch (err) { /* keep empty prefs */ }
        }
        return {};
    }

    function isGuest(uid) {
        return !uid || uid === 'default_user';
    }

    function setStatus(text) {
        var el = document.getElementById('shop-pm-status');
        if (el) el.textContent = text || '';
    }

    function setAccountLabel(name, uid) {
        var nameEl = document.getElementById('shop-profile-display-name');
        if (!nameEl) return;
        nameEl.dataset.ready = '1';
        nameEl.textContent = name || (isGuest(uid) ? 'Guest checkout' : 'Your account');
    }

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function ledgerTable(rows) {
        var body = rows.map(function (row) {
            return '<tr><th scope="row">' + escapeHtml(row[0]) + '</th><td>' + escapeHtml(row[1]) + '</td></tr>';
        }).join('');
        return '<div class="shop-table-wrap"><table class="shop-table"><thead><tr><th>Linked to shop</th><th>Now</th></tr></thead><tbody>' + body + '</tbody></table></div>';
    }

    async function readJson(url, options) {
        var response = await fetch(url, options || { credentials: 'same-origin', cache: 'no-store' });
        var data = await response.json().catch(function () { return {}; });
        return { ok: response.ok, status: response.status, data: data };
    }

    async function bindSession(uid, password) {
        var body = { user_id: uid };
        if (password) body.password = password;
        var out = await readJson('/api/user/bind-session', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (out.status === 401 && out.data && out.data.requires_password) {
            var pwd = window.prompt('Password required to bind this account:');
            if (!pwd) return { ok: false, data: { error: 'Password required' } };
            return bindSession(uid, pwd);
        }
        return out;
    }

    function rememberAccount(uid) {
        localStorage.setItem('game_user_id', uid);
        localStorage.setItem('user_id', uid);
    }

    function reloadShop() {
        window.setTimeout(function () { window.location.reload(); }, 350);
    }

    async function loadLedger(uid, profile) {
        var slot = document.getElementById('shop-pm-ledger');
        if (!slot) return;
        var coins = '—';
        var mn2 = '—';
        var orders = '—';
        try {
            var pack = await Promise.all([
                readJson('/api/game/shop/currency?user_id=' + encodeURIComponent(uid)),
                readJson('/api/mn2/balance?user_id=' + encodeURIComponent(uid)),
                readJson('/api/shop/purchases?user_id=' + encodeURIComponent(uid) + '&limit=5')
            ]);
            if (pack[0].data && pack[0].data.success) coins = String(pack[0].data.currency || 0);
            if (pack[1].data && pack[1].data.mn2_balance != null) mn2 = String(pack[1].data.mn2_balance);
            if (pack[2].data && Array.isArray(pack[2].data.purchases)) orders = String(pack[2].data.purchases.length);
        } catch (err) {
            coins = 'unavailable';
        }
        var name = (profile && (profile.display_name || profile.username)) || '—';
        slot.innerHTML = ledgerTable([
            ['Account id', uid],
            ['Display name', name],
            ['Coins', coins],
            ['MN2', mn2],
            ['Recent orders', orders]
        ]);
    }

    async function loadProfile() {
        var uidInput = document.getElementById('shop-pm-user-id');
        var nameInput = document.getElementById('shop-pm-display-name');
        var bioInput = document.getElementById('shop-pm-bio');
        if (!uidInput) return;
        var uid = uidStored();
        uidInput.value = uid;
        setAccountLabel('', uid);
        if (isGuest(uid)) {
            setStatus('Guests can browse. Create an account before PayPal, gifting, or selling.');
        }
        try {
            var out = await readJson('/api/user/profile/' + encodeURIComponent(uid) + '/display');
            var profile = out.ok && out.data.profile ? out.data.profile : null;
            prefsCache = asObject(profile && profile.preferences);
            if (nameInput) nameInput.value = profile ? (profile.display_name || profile.username || '') : '';
            if (bioInput) bioInput.value = profile ? (profile.bio || '') : '';
            if (profile) {
                setAccountLabel(profile.display_name || profile.username, uid);
                if (!isGuest(uid)) setStatus('This shop account is the same profile as /profile.');
            } else if (!isGuest(uid)) {
                setStatus((out.data && out.data.error) || 'No profile yet. Create the account to connect checkout.');
            }
            await loadLedger(uid, profile);
        } catch (err) {
            setStatus('Could not reach the profile service. You can still create or log in.');
        }
    }

    async function createAccount() {
        var uid = (document.getElementById('shop-pm-user-id').value || '').trim();
        var displayName = (document.getElementById('shop-pm-display-name').value || '').trim();
        if (!uid || isGuest(uid)) {
            setStatus('Choose an account id that is not default_user.');
            return;
        }
        setStatus('Creating account…');
        var out = await readJson('/api/user/create', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: uid,
                referral_source: 'shop',
                landing_page: '/shop',
                preferences: displayName ? { display_name: displayName } : {}
            })
        });
        if (!out.data || !out.data.success) {
            setStatus((out.data && out.data.error) || 'Create failed');
            return;
        }
        rememberAccount(uid);
        await bindSession(uid);
        setStatus('Account created. Reloading the shop on this profile…');
        reloadShop();
    }

    async function loginAccount() {
        var uid = (document.getElementById('shop-pm-user-id').value || '').trim();
        if (!uid) {
            setStatus('Enter an account id first.');
            return;
        }
        setStatus('Logging in…');
        var body = { user_id: uid, auto_create: false };
        var out = await readJson('/api/user/login', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (out.data && out.data.requires_password) {
            var pwd = window.prompt('This account requires a password to log in:');
            if (!pwd) {
                setStatus('Password required to log in.');
                return;
            }
            body.password = pwd;
            out = await readJson('/api/user/login', {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
        }
        if (!out.data || !out.data.success) {
            setStatus((out.data && out.data.error) || 'Login failed');
            return;
        }
        rememberAccount(uid);
        await bindSession(uid, body.password);
        setStatus('Logged in. Reloading the shop…');
        reloadShop();
    }

    async function useAccount() {
        var uid = (document.getElementById('shop-pm-user-id').value || '').trim() || 'default_user';
        setStatus('Connecting this id to the shop…');
        var out = await bindSession(uid);
        rememberAccount(uid);
        setStatus(out.ok && out.data && out.data.success ? 'Session saved. Reloading…' : ((out.data && out.data.error) || 'Saved on this device. Reloading…'));
        reloadShop();
    }

    async function logoutAccount() {
        try {
            await readJson('/api/user/logout', { method: 'POST', credentials: 'same-origin' });
        } catch (err) { /* local logout still proceeds */ }
        localStorage.removeItem('game_user_id');
        localStorage.removeItem('user_id');
        setStatus('Logged out on this device.');
        reloadShop();
    }

    async function saveProfile(event) {
        event.preventDefault();
        var uid = (document.getElementById('shop-pm-user-id').value || '').trim();
        var stored = uidStored();
        if (uid !== stored) {
            setStatus('Click Use this id so the shop and this form share one account, then save.');
            return;
        }
        if (isGuest(uid)) {
            setStatus('Create an account before saving a display name.');
            return;
        }
        var displayName = (document.getElementById('shop-pm-display-name').value || '').trim();
        var bio = (document.getElementById('shop-pm-bio').value || '').trim();
        var preferences = Object.assign({}, prefsCache, {
            display_name: displayName,
            bio: bio
        });
        setStatus('Saving profile…');
        var out = await readJson('/api/user/profile/update', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: uid,
                update_data: {
                    username: displayName || uid,
                    preferences: preferences
                }
            })
        });
        if (!out.data || !out.data.success) {
            setStatus((out.data && out.data.error) || 'Save failed');
            return;
        }
        prefsCache = preferences;
        setAccountLabel(displayName || uid, uid);
        setStatus('Saved. Profile and shop now share this name.');
        await loadLedger(uid, { display_name: displayName, username: uid, bio: bio });
    }

    function goShop(action, focusId) {
        if (action && action.indexOf('purchase:') === 0) {
            var itemId = action.slice('purchase:'.length);
            if (typeof window.purchaseItem === 'function') window.purchaseItem(itemId);
            return;
        }
        if (action === 'boosts') {
            var sel = document.getElementById('shop-category-select');
            if (sel) {
                sel.value = 'boosts';
                sel.dispatchEvent(new Event('change'));
            }
            return;
        }
        if (action && typeof window.showShopTab === 'function') window.showShopTab(action);
        if (focusId) {
            var node = document.getElementById(focusId);
            if (node && node.scrollIntoView) node.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    async function featureListing(event) {
        event.preventDefault();
        var status = document.getElementById('shop-feature-status');
        var listingId = (document.getElementById('shop-feature-listing-id').value || '').trim();
        var uid = uidStored();
        if (isGuest(uid)) {
            if (status) status.textContent = 'Create a profile before paying to feature a listing.';
            return;
        }
        if (!listingId) {
            if (status) status.textContent = 'Paste a listing id from My Stall.';
            return;
        }
        if (status) status.textContent = 'Featuring…';
        var out = await readJson('/api/shop/auction/feature', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: uid, listing_id: listingId, payment_method: 'coins' })
        });
        if (status) {
            status.textContent = (out.data && out.data.success)
                ? 'Listing featured. It floats to the top of the market.'
                : ((out.data && out.data.error) || 'Could not feature that listing.');
        }
        if (out.data && out.data.success && typeof window.showShopTab === 'function') {
            window.showShopTab('auction');
        }
    }

    function bind() {
        var form = document.getElementById('shop-profile-form');
        if (form && !form.dataset.bound) {
            form.dataset.bound = '1';
            form.addEventListener('submit', saveProfile);
            document.getElementById('shop-pm-create').addEventListener('click', createAccount);
            document.getElementById('shop-pm-login').addEventListener('click', loginAccount);
            document.getElementById('shop-pm-use').addEventListener('click', useAccount);
            document.getElementById('shop-pm-logout').addEventListener('click', logoutAccount);
        }
        var feature = document.getElementById('shop-feature-form');
        if (feature && !feature.dataset.bound) {
            feature.dataset.bound = '1';
            feature.addEventListener('submit', featureListing);
        }
        if (!document.body.dataset.shopGoBound) {
            document.body.dataset.shopGoBound = '1';
            document.body.addEventListener('click', function (event) {
                var el = event.target.closest('[data-shop-go]');
                if (!el) return;
                event.preventDefault();
                goShop(el.getAttribute('data-shop-go'), el.getAttribute('data-shop-focus'));
            });
        }
    }

    window.ShopProfileManager = {
        open: loadProfile
    };

    function boot() {
        bind();
        loadProfile();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot);
    } else {
        boot();
    }
})();
