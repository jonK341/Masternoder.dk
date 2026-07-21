# MN2 Explorer — Runbooks

## eiquidus index stuck (#217)

**Symptoms:** Rich list empty, address pages 404, `explorer/status` shows `rich_list.index_synced: false`, supply API works but rich-list does not.

**Checks:**

```bash
curl -sS http://127.0.0.1:3000/ext/getmoneysupply
curl -sS http://127.0.0.1:3000/ext/getaddressbalance?address=<addr>
curl -sS https://<site>/api/mn2/explorer/status | jq '.checks.rich_list'
```

**Steps:**

1. Confirm daemon has `txindex=1` and address indexes enabled; reindex if flags were recently flipped (see [EXPLORER_REINSTALL_CHECKLIST.md](EXPLORER_REINSTALL_CHECKLIST.md)).
2. Check eiquidus PM2/logs for sync errors; restart: `pm2 restart eiquidus` (name may vary).
3. Run iquidus sync cron manually once; wait for block height to match daemon `getblockcount`.
4. If Mongo is corrupt: **backup first** (`scripts/backup_eiquidus_mongo.sh`), then follow reinstall checklist.
5. Hub shows empty-state copy until index catches up — no code change required.

---

## Chainz fallback activation (#218)

**When:** Self-hosted eiquidus down, wrong `explorer_kind`, or RPC unreachable and tiles need external data.

**Flip to Chainz-only (temporary):**

```bash
# In server .env
MN2_EXPLORER_KIND=chainz
MN2_EXPLORER_BASE_URL=https://chainz.cryptoid.info/mn2/
MN2_EXPLORER_FALLBACK_BASE_URL=https://chainz.cryptoid.info/mn2/
```

Deploy env: `python scripts/deploy.py mn2_env --ask-pass`

**Verify:**

```bash
curl -sS https://<site>/api/mn2/network-overview | jq '.explorer_kind, .source'
python scripts/smoke_explorer_deploy.py --base-url https://<site>
```

**Restore iquidus:** set `MN2_EXPLORER_KIND=iquidus` and self-hosted base URL; see [MN2_OPS.md §10](MN2_OPS.md) blue/green notes in [EXPLORER_OPS_P4.md](EXPLORER_OPS_P4.md).

Rollback doc for Chainz-only is item #178 in [EXPLORER_UPGRADES_250.md](EXPLORER_UPGRADES_250.md).
