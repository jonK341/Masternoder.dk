# MN2 hosting fleet & rental — deployment checklist

Use after merging the treasury / fleet / rental PR and before opening **$5/month** leases to the public.

## 1. Wallet & treasury

- [ ] Confirm ops `wallet.dat` under `/var/www/html/config` holds enough MN2 for collateral (500 × 5,000 = **2.5M** plus fees).
- [ ] If live wallet was empty, restore from `backups/wallet.dat.*` and restart the MN2 daemon.
- [ ] Run (dry-run first) treasury → preferred wallet move:
  - `python scripts/mn2_agent_treasury_to_preferred_remote.py --dry-run`
  - then without `--dry-run` when balances look correct.
- [ ] Unlock exchange liquidity if collateral UTXOs are locked in sells:
  - `scripts/mn2_free_exchange_liquidity_remote.py`

## 2. Fleet bootstrap (500 slots)

- [ ] Upload code + `data/mn2_masternode_config.json` (`max_hosted_nodes`: 500).
- [ ] Start bootstrap (tmux): `python scripts/mn2_bootstrap_fleet_inventory_remote.py`
- [ ] Monitor: `python scripts/mn2_bootstrap_fleet_inventory_remote.py --status`
  - Log: `/var/www/html/logs/mn2_fleet_bootstrap.log`
  - Progress: `/var/www/html/data/mn2_fleet_bootstrap_progress.json`
- [ ] Wait until progress shows funding complete, `platform-mn-*` hosts seeded, and most nodes **active** on-chain.

## 3. App deploy

- [ ] Deploy branch with rental API, hosting hub UI, and `mn2_masternode_hosting_rewards_service`.
- [ ] Health: `GET /api/health` → healthy.
- [ ] Hosting: `GET /api/mn2/masternode/service` → sensible `slots_available` / fleet counts.
- [ ] Rental catalog: `GET /api/mn2/masternode/rentals/catalog` → `inventory_available` > 0 when fleet is ready.

## 4. PayPal & monetization

- [ ] Replace placeholder plan **`P-PLACEHOLDER-MN-HOST`** in `data/monetization_config.json` with a **live** PayPal billing plan at **$5/month** (or per 30-day period).
- [ ] Smoke: `python scripts/mn_hosting_paypal_smoke.py` (capture only if intentional).
- [ ] Subscribe button on `/hosting/` should return an approve URL, not `plan_not_live`.

## 5. Crons (renter rewards + provisioning)

- [ ] `/etc/cron.d/masternoder-mn2-accrue` installed (hourly `cron/mn2_accrue_rewards.sh`) — includes  
  `POST /api/mn2/masternode/accrue-renter-rewards`.
- [ ] `/etc/cron.d/masternoder-mn2-masternode-provision` — also calls accrue after `provision-pending`.
- [ ] `MN2_OPS_SECRET` (or `MN2_SCAN_SECRET`) set in `/var/www/html/.env`.

**Manual ops test (on server):**

```bash
source /var/www/html/cron/mn2_read_ops_secret.sh
SECRET=$(mn2_read_ops_secret)
curl -s -X POST -H "X-Ops-Token: $SECRET" \
  "http://127.0.0.1:5000/api/mn2/masternode/accrue-renter-rewards?dry_run=1" | python3 -m json.tool
```

## 6. Renter rewards verification

- [ ] Assign a test lease (inventory order or ops `assign_rental_hosts` path).
- [ ] Confirm `data/mn2_masternode_renter_rewards_state.json` has a `lastpaid` baseline for the host (seeded at assignment).
- [ ] After a real on-chain payout advance, run accrue (no dry_run) and confirm:
  - Renter `mn2_balance` increased via ledger source `masternode_hosting_payout`.
  - `GET /api/mn2/masternode/my-hosting-rewards?user_id=…` returns totals.
- [ ] Hosting hub **Overview** shows “Your masternode rewards” when signed in.

## 7. UI smoke

- [ ] `/hosting/` — **Lease inventory** vs **Provision new**, inventory count, checkout rails.
- [ ] PayPal return lands on hosting hub and order appears under **My orders**.

## Quick rollback notes

- Disable leases: set `rental.enabled` to `false` in `mn2_masternode_config.json` and reload app.
- Disable reward credits: set `renter_rewards.enabled` to `false` (accrue becomes no-op).
