# MN2 shop and addresses

## Which address does the shop use for MN2 purchases?

**In-app "Pay with MN2"** does not send coins on-chain at purchase time. We deduct from the user's in-app `mn2_balance` (unified points). That balance was funded when the user **deposited** MN2 to their per-user deposit address — which is an address from the **site's daemon wallet**. So:

- **No separate "shop receiving address" is required.** All MN2 is already in the same daemon wallet (the one that owns every per-user deposit address). Shop revenue is just the net of deposits minus withdrawals, tracked in the ledger.
- **Optional:** For accounting or display (e.g. "Shop treasury"), you can set a dedicated **`shop_revenue_address`** in `data/mn2_config.json`: one address from your wallet (e.g. from a one-time `getnewaddress`), used only for labelling. The backend does not send shop payments to this address; it is for reporting or future "pay merchant address" flows.

## Config

In `data/mn2_config.json`:

- **`shop_revenue_address`** (optional): Leave empty `""` for default behaviour. If set to an MN2 address (e.g. your receiving/treasury address), it is shown in the **MN2 Wallet** section on both the **Shop** and **Profile** pages as "Shop revenue address" with Copy and "View on explorer" links. No backend logic sends user payments to this address on purchase — it is for display and transparency.

Current value: `JNKzUoRpc7nhnPKZkzxJe4Vkmaz82o8jiX` (receiving address for shop revenue).
