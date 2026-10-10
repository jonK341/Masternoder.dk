# MN2 shop and addresses

## Which address does the shop use for MN2 purchases?

**In-app "Pay with MN2"** does not send coins on-chain at purchase time. We deduct from the user's in-app `mn2_balance` (unified points). That balance was funded when the user **deposited** MN2 to their per-user deposit address — which is an address from the **site's daemon wallet**. So:

- **No separate "shop receiving address" is required.** All MN2 is already in the same daemon wallet (the one that owns every per-user deposit address). Shop revenue is just the net of deposits minus withdrawals, tracked in the ledger.
- **Optional:** For accounting or display (e.g. "Shop treasury"), you can set a dedicated **`shop_revenue_address`** in `data/mn2_config.json`: one address from your wallet (e.g. from a one-time `getnewaddress`), used only for labelling. The backend does not send shop payments to this address; it is for reporting or future "pay merchant address" flows.

## Config

In `data/mn2_config.json`:

- **`shop_revenue_address`** (optional): Leave empty `""` for default behaviour. If set to an MN2 address (e.g. your receiving/treasury address), it is shown in the **MN2 Wallet** section on both the **Shop** and **Profile** pages as "Shop revenue address" with Copy and "View on explorer" links. No backend logic sends user payments to this address on purchase — it is for display and transparency.

Current value: `JNKzUoRpc7nhnPKZkzxJe4Vkmaz82o8jiX` (receiving address for shop revenue).

## How new addresses are created

Every new receive address is created by `mn2_wallet_service.generate_daemon_address()`. That is the only call to daemon `getnewaddress`. It retries when the wallet is locked: if `MN2_WALLET_PASSPHRASE` is set it unlocks for keypool use (`walletpassphrase`, staking-only false) and asks again. Deposit addresses, shop order payments, encoder orders, masternode collateral, hosting quotes, and the agent treasury all use this function, then keep the user→address map in `data/mn2_user_addresses.json`.

Signup (`POST /api/user/create`) and first identification call `ensure_user_address`, which creates that address and, when the daemon allows it, labels it with `setlabel` or `setaccount` = `user_id`. If those RPCs are missing, the JSON map is the label.

Existing users are filled by `scripts/mn2_backfill_user_addresses.py`:

- `--dry-run` (default) prints the next batch and does not call the daemon.
- `--apply` creates addresses only for users who do not already have one, and writes `logs/mn2_address_backfill_state.json` after each user so a rerun resumes.
- `--batch-size` limits each invocation. Run `--apply` until `batch_count` is 0.

`POST /api/mn2/ops/backfill-addresses` is the same plan; pass `{"apply": true}` to create. Ops secret rules match the other `/api/mn2/ops/*` routes.

## On-chain wallet and who pays the fee

`wallet_mode` in `data/mn2_config.json` is `ledger` or `onchain`. It defaults to `ledger`, so shop MN2 purchases keep debiting in-app `mn2_balance` until the owner flips it.

Profile and Shop render the same balance payload: ledger `mn2_balance` plus on-chain confirmed/unconfirmed from `listunspent` filtered to that user's addresses, and a reconcile delta.

User-to-user transfer (`POST /api/mn2/transfer` to a user id or one of our deposit addresses) builds one transaction:

- Inputs from the sender's address pay the full amount. Change goes back to the sender.
- Inputs from `onchain_fee_payer.address` pay `onchain_fee_payer.network_fee_mn2`. Change goes back to the fee payer.
- The miner fee is that network fee, so the site pays it. The ledger records `site_network_fee` on `onchain_fee_payer.user_id` (default `@site_fee_payer`). If the payer's remaining balance is below `low_balance_mn2`, a line is appended to `logs/mn2_fee_payer_alerts.jsonl`.

This requires `createrawtransaction`, `signrawtransactionwithwallet` (or `signrawtransaction`), and `sendrawtransaction`. `sendfrom` is detected but is not used for fee separation, because it cannot attach a second fee-payer input. If those raw RPCs are missing, the transfer returns `per_address_send_unsupported` and does not fall back to wallet-wide `sendtoaddress` (that would take the fee from arbitrary wallet coins).

External withdrawals (`POST /api/mn2/withdraw`, and transfer to an address that is not a site user) keep the existing checks: session auth, password gate, whitelist, new-address cooldown, daily limits, and `withdrawal_fee` taken from the user. Set `onchain_fee_payer.pay_external_withdrawal_fee` to true only when the site should pay that fee too; the send then uses the same coin-control path and the user is charged no `withdrawal_fee`.

Shop purchases with `wallet_mode: onchain` pay `shop_revenue_address` the same way (site pays the miner fee). `ledger` does not.

Trade-offs: each transfer or on-chain purchase waits for a broadcast and then for confirmations (`confirmations` in config, shown as confirmed vs unconfirmed). The site must keep the fee-payer address topped up or sends fail with `fee_payer_insufficient`. A raw transaction also costs a network fee even though the user does not pay it.
