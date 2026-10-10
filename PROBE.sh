#!/usr/bin/env bash
# READ-ONLY probe. Run on the server from /var/www/html. Prints schema/column NAMES
# and JSON key NAMES only -- it masks addresses and never prints secret values.
# Purpose: (A) confirm the real shop_purchases columns, (B) locate the MN2
# address-book / state file, (C) report its shape, (D) see how the service stores it.
set -uo pipefail
cd /var/www/html
PY=.venv/bin/python
DB=instance/database.db

echo "===== A. real shop_purchases schema ====="
$PY - "$DB" <<'PY'
import sqlite3,sys
c=sqlite3.connect(sys.argv[1])
cols=[r[1] for r in c.execute("PRAGMA table_info(shop_purchases)")]
print("shop_purchases columns:", cols)
print("row count:", c.execute("SELECT COUNT(*) FROM shop_purchases").fetchone()[0])
# show which amount-like columns actually exist
cand=[x for x in cols if x.lower() in
      {"amount","mn2_amount","price","cost","total","value","purchase_amount","price_mn2"}]
print("amount-like columns present:", cand or "NONE")
ucand=[x for x in cols if x.lower() in {"user_id","userid","uid","owner_id","account_id","user"}]
print("user-like columns present:", ucand or "NONE")
PY

echo; echo "===== B. locate MN2 state / address-book files ====="
ls -la data/ 2>/dev/null | head -40
echo "--- find mn2 / address-book json (bounded) ---"
find . -path ./node_modules -prune -o \( -iname '*mn2*.json' -o -iname '*address*book*' \) -print 2>/dev/null | head -30

echo; echo "===== C. shape of each MN2 json (KEY NAMES only, values masked) ====="
$PY - <<'PY'
import json,glob,os
hits=[]
for pat in ["data/mn2_*.json","data/*address*book*.json","backend/data/mn2_*.json",
            "instance/mn2_*.json","**/mn2_address_book.json"]:
    hits+=glob.glob(pat,recursive=True)
hits=sorted(set(h for h in hits if os.path.isfile(h)))[:15]
if not hits: print("  (no mn2 json files found)")
for f in hits:
    try:
        d=json.load(open(f)); sz=os.path.getsize(f)
        if isinstance(d,dict):
            k=list(d)[:3]; v=d[k[0]] if k else None
            s=f"dict({len(d)} keys) sample_keys={k} val_type={type(v).__name__}"
            if isinstance(v,dict): s+=f" val_keys={list(v)[:10]}"
            elif isinstance(v,list): s+=f" len={len(v)} elem0={ (list(v[0])[:8] if v and isinstance(v[0],dict) else type(v[0]).__name__ if v else 'empty') }"
        elif isinstance(d,list):
            s=f"list({len(d)}) elem0_keys={list(d[0])[:10] if d and isinstance(d[0],dict) else 'n/a'}"
        else: s=type(d).__name__
        print(f"  {f} ({sz}B): {s}")
    except Exception as e: print(f"  {f}: ERR {e}")
PY

echo; echo "===== D. how the service stores user->address ====="
for f in $(find backend -maxdepth 3 \( -name 'mn2_wallet_service.py' -o -name 'mn2_address_book.py' -o -name 'mn2_micro_transactions_service.py' \) 2>/dev/null | head -3); do
  echo "--- $f ---"
  grep -nE "_PATH|_FILE|os\.path\.join|open\(|json\.(load|dump)|CREATE TABLE|INSERT INTO|\.db|data/|sqlite" "$f" | head -20
done

echo; echo ">>> Paste ALL of the above back. Then re-run steps 3-5 of the migration"
echo ">>> (backfill is idempotent; schema is already applied):"
echo ">>>   .venv/bin/python migrations/002_backfill_mn2.py --db instance/database.db --book <PATH_FROM_B>"
echo ">>>   .venv/bin/python migrations/003_crawl_site_pages.py --db instance/database.db --no-html"
echo ">>>   .venv/bin/python migrations/004_verify.py instance/database.db"
