# PayPal Integration Guide — Real Money in MasterNoder

**Goal:** Connect your PayPal Pro account so users can pay real dollars for shop items, premium features, and agent-driven monetization.

**Related:** [MONETIZATION_PAYPAL.md](./MONETIZATION_PAYPAL.md) — revenue models (packs, tiers, subscriptions, B2B), rollout order, and code touchpoints.

---

## Quick Start (3 steps)

1. **Get credentials** from [developer.paypal.com](https://developer.paypal.com) → My Apps & Credentials.
2. **Add to `.env`**:
   ```
   PAYPAL_CLIENT_ID=your_client_id
   PAYPAL_CLIENT_SECRET=your_secret
   PAYPAL_MODE=sandbox
   ```
3. **Restart Flask** — the PayPal blueprint is already registered. Test with:
   ```bash
   curl -X POST http://localhost:5000/vidgenerator/api/paypal/create-order \
     -H "Content-Type: application/json" \
     -d '{"amount": 1.00, "item_name": "Test"}'
   ```

The service (`paypal_service.py`) and routes (`paypal_routes.py`) are in place. Add "Pay with PayPal" buttons in the shop UI as described below.

---

## 1. Prerequisites

- **PayPal Business / Pro account** ✅ (you have this)
- **PayPal Developer credentials** (Client ID + Secret)
- **Flask app** (already in place)
- **Shop system** (coins + unified_points — we add `paypal`)

---

## 2. Get PayPal API Credentials

1. Go to [developer.paypal.com](https://developer.paypal.com) and log in with your PayPal account.
2. **Dashboard** → **My Apps & Credentials**.
3. Under **REST API apps**, create an app (or use existing).
4. Copy:
   - **Client ID**
   - **Secret** (click "Show" to reveal)
5. For testing: use **Sandbox** credentials.  
   For production: use **Live** credentials.

---

## 3. Environment Variables

Add to `.env` (never commit secrets to git):

```env
# PayPal (Sandbox for testing)
PAYPAL_CLIENT_ID=your_client_id_here
PAYPAL_CLIENT_SECRET=your_secret_here
PAYPAL_MODE=sandbox

# For production, switch to:
# PAYPAL_MODE=live

# Purchase notifications (email + log when someone buys)
NOTIFY_ADMIN_EMAIL=your@email.com
# Optional SMTP (Gmail: use App Password)
NOTIFY_SMTP_HOST=smtp.gmail.com
NOTIFY_SMTP_PORT=587
NOTIFY_SMTP_USER=your@gmail.com
NOTIFY_SMTP_PASSWORD=your_app_password
NOTIFY_SMTP_USE_TLS=true
```

---

## 4. Install Dependencies

```bash
pip install requests
```

No official PayPal Python SDK needed — use REST API with `requests`.

---

## 5. PayPal Service Module

**Already created:** `backend/services/paypal_service.py`

The service handles OAuth, `create_order`, and `capture_order`. It uses `PAYPAL_MODE=sandbox` for testing and `live` for production.

---

## 6. PayPal Routes

**Already created:** `backend/routes/paypal_routes.py` — `GET/POST /vidgenerator/api/paypal/create-order` and `/vidgenerator/api/paypal/capture`. On success, capture adds `monetization_points` to the user.

## 7. Blueprint Registration

**Already registered** in `backend/register_blueprints.py`.

---

## 8. Shop Integration — Add PayPal Price Type

### 8.1 Add PayPal-priced items

In `shop_routes.py` or your shop seed, add items with `price_type: 'paypal'`:

```python
# Example: Premium item for real money
{
    "id": "premium-theme-pack",
    "name": "Premium Theme Pack",
    "description": "All premium themes — real purchase",
    "category": "premium",
    "price_type": "paypal",
    "price_usd": 4.99,
    "icon": "🎨",
    "rarity": "legendary",
}
```

### 8.2 Purchase flow for PayPal

When user clicks "Buy with PayPal":

1. Frontend calls `POST /vidgenerator/api/paypal/create-order` with `{ amount, item_id, item_name, user_id }`.
2. Backend returns `approve_url`.
3. Frontend redirects: `window.location.href = approve_url`.
4. User pays on PayPal, returns to your `return_url` (e.g. `/vidgenerator/shop?paypal=success&token=ORDER_ID`).
5. Frontend (on load if `paypal=success`) calls `POST /vidgenerator/api/paypal/capture` with `order_id`.
6. Backend captures, then:
   - Grants item to user (inventory)
   - Adds `monetization_points` or `cash_points` to unified points
   - Records in `shop_purchases` with `price_type='paypal'`, `price_paid_usd=4.99`

---

## 9. Frontend — Shop "Pay with PayPal" Button

In `vidgenerator/shop/index.html` (or your shop UI), add:

```html
<button class="paypal-btn" data-item-id="premium-theme-pack" data-amount="4.99" data-name="Premium Theme Pack">
    Pay with PayPal
</button>
```

```javascript
document.querySelectorAll('.paypal-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const itemId = btn.dataset.itemId;
        const amount = parseFloat(btn.dataset.amount);
        const name = btn.dataset.name;
        const userId = localStorage.getItem('game_user_id') || 'default_user';

        const res = await fetch('/vidgenerator/api/paypal/create-order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount, item_id: itemId, item_name: name, user_id: userId }),
        });
        const data = await res.json();
        if (data.success && data.approve_url) {
            window.location.href = data.approve_url;
        } else {
            alert('Error: ' + (data.error || 'Could not create order'));
        }
    });
});

// On return from PayPal (URL has ?paypal=success&token=...)
const params = new URLSearchParams(location.search);
if (params.get('paypal') === 'success' && params.get('token')) {
    const orderId = params.get('token');
    const res = await fetch('/vidgenerator/api/paypal/capture', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order_id: orderId }),
    });
    const data = await res.json();
    if (data.success) {
        alert('Payment successful! Item added to your account.');
        // Clear URL params
        history.replaceState({}, '', location.pathname);
    }
}
```

---

## 10. Connect to Monetization & Agents

After a successful capture:

1. **Unified points:**  
   `unified_points_db.add_points(user_id, 'monetization_points', amount * 100, source='paypal', metadata={...})`  
   (or use `cash_points` if you prefer)

2. **Shop purchase record:**  
   Extend `record_purchase()` to support `price_type='paypal'` and `price_paid_usd`.

3. **Agent-driven monetization:**  
   When an agent triggers a premium action (e.g. "Generate 30s video for $2"), create a PayPal order for that amount and link it to the agent task.

---

## 11. Checklist

| Step | Action |
|------|--------|
| 1 | Get Client ID + Secret from developer.paypal.com |
| 2 | Add `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE` to `.env` |
| 3 | Create `backend/services/paypal_service.py` |
| 4 | Create `backend/routes/paypal_routes.py` |
| 5 | Register `paypal_bp` in `register_blueprints.py` |
| 6 | Add PayPal-priced items to shop |
| 7 | Add "Pay with PayPal" button + return/capture logic in shop UI |
| 8 | Extend `record_purchase` for `price_type='paypal'` |
| 9 | Test with Sandbox, then switch to Live |

---

## 12. PayPal Pro / Advanced Features

With a **PayPal Pro** account you can also:

- **Card processing** — Accept cards without redirect (PayPal Advanced Card Processing).
- **Subscriptions** — Use Subscriptions API for recurring payments.
- **Payouts** — Use Payouts API to send money (e.g. to agents or creators).

For most shop flows, the standard **Orders v2** flow above is enough. Add Pro features as needed.

---

## 13. Security Notes

- Never expose Client Secret in frontend.
- Validate `amount` server-side; never trust client.
- Use HTTPS in production.
- Store `order_id` in session or DB when creating, and verify it matches on capture.
- Consider webhooks for async confirmation (optional).

---

## 14. Quick Test (Sandbox)

1. Create order:  
   `curl -X POST http://localhost:5000/vidgenerator/api/paypal/create-order -H "Content-Type: application/json" -d '{"amount": 1.00, "item_name": "Test"}'`
2. Open returned `approve_url` in browser.
3. Log in with a [Sandbox test account](https://developer.paypal.com/dashboard/accounts).
4. Approve payment.
5. Call capture with the returned `order_id`.

---

## 15. Production Checklist

Before going live with real payments:

| Check | Status |
|-------|--------|
| `PAYPAL_MODE=live` (exactly, no extra text) | Required |
| Live credentials from [developer.paypal.com](https://developer.paypal.com) → My Apps → Live | Required |
| `BASE_URL` = site origin, e.g. `https://masternoder.dk` (no trailing `/vidgenerator`) | Required |
| `SECRET_KEY` changed from default | Required |
| HTTPS enabled on site | Required |
| `NOTIFY_ADMIN_EMAIL` set for purchase alerts | Recommended |
| Test a real $0.99 purchase (smallest coin pack) | Recommended |

**Return URL:** PayPal redirects to `{BASE_URL}/vidgenerator/shop?paypal=success&token=...`. Ensure your site serves this URL over HTTPS.

---

**Summary:** With this setup, your shop can accept real dollars via PayPal. The agent can drive monetization by triggering premium actions that create PayPal orders. Your existing unified points and shop infrastructure stay in place; PayPal becomes an additional `price_type` alongside coins and unified points.
