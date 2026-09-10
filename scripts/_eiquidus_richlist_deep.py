#!/usr/bin/env python3
"""Deep diagnostic: eiquidus rich list + MN2 health probe on server."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
cd /var/www/explorer

echo '== grep health probe on app =='
grep -rn 'explorer_probe\|rich_list\|getrichlist' /var/www/html/backend 2>/dev/null | head -20

echo '== eiquidus routes (rich/address) =='
grep -rn 'richlist\|rich_list\|getaddresslist\|getrichlist' routes lib 2>/dev/null | head -25

echo '== settings.json mongo =='
python3 - <<'PY'
import json
try:
    s=json.load(open('settings.json'))
    db=s.get('database',{})
    print('db:', {k:('***' if k=='password' else v) for k,v in db.items()})
except Exception as e:
    print('settings_err', e)
PY

echo '== mongo counts (settings creds) =='
node - <<'NODE'
const fs=require('fs');
let s={}; try{s=JSON.parse(fs.readFileSync('settings.json','utf8'));}catch(e){}
const db=s.database||{};
const {MongoClient}=require('mongodb');
const host=db.host||'127.0.0.1';
const port=db.port||27017;
const user=db.user||'';
const pass=db.password||'';
const name=db.database||'explorerdb';
const auth=db.authSource||name;
const uri=user?`mongodb://${encodeURIComponent(user)}:${encodeURIComponent(pass)}@${host}:${port}/${name}?authSource=${auth}`:`mongodb://${host}:${port}/${name}`;
(async()=>{
  let client;
  try{
    client=new MongoClient(uri,{serverSelectionTimeoutMS:5000});
    await client.connect();
    const d=client.db(name);
    const cols=await d.listCollectionNames().toArray();
    console.log('collections', cols.slice(0,20));
    for (const c of ['blocks','addresses','richlist','stats']){
      try{ console.log(c, await d.collection(c).estimatedDocumentCount()); }catch(e){ console.log(c,'err',e.message); }
    }
    const sample=await d.collection('addresses').find().sort({balance:-1}).limit(3).project({a_id:1,balance:1}).toArray();
    console.log('top_addresses', JSON.stringify(sample));
    const rl=await d.collection('richlist').find().limit(3).toArray();
    console.log('richlist_sample', JSON.stringify(rl));
  }catch(e){ console.log('mongo_fail', e.message); }
  finally{ if(client) await client.close(); }
})();
NODE

echo '== probe ext/api paths =='
for p in \
  '/ext/getrichlist?page=0' \
  '/ext/getaddresslist?page=0' \
  '/ext/getdistribution' \
  '/ext/getaddresstotal' \
  '/api/getaddressbalance/M7xxx' \
  '/ext/summary' \
  ; do
  code=$(curl -sS -m 8 -o /tmp/probe.txt -w '%{http_code}' "http://127.0.0.1:3000$p")
  ct=$(head -c 80 /tmp/probe.txt | tr '\n' ' ')
  echo "$code $p :: $ct"
done

echo '== sync.js index help =='
node scripts/sync.js index 2>&1 | head -15

echo '== stats doc =='
node - <<'NODE'
const fs=require('fs');
let s={}; try{s=JSON.parse(fs.readFileSync('settings.json','utf8'));}catch(e){}
const db=s.database||{};
const {MongoClient}=require('mongodb');
const host=db.host||'127.0.0.1';
const port=db.port||27017;
const user=db.user||'';
const pass=db.password||'';
const name=db.database||'explorerdb';
const auth=db.authSource||name;
const uri=user?`mongodb://${encodeURIComponent(user)}:${encodeURIComponent(pass)}@${host}:${port}/${name}?authSource=${auth}`:`mongodb://${host}:${port}/${name}`;
(async()=>{
  let client;
  try{
    client=new MongoClient(uri);
    await client.connect();
    const st=await client.db(name).collection('stats').findOne();
    console.log(JSON.stringify(st,null,2));
  }catch(e){ console.log('stats_err', e.message); }
  finally{ if(client) await client.close(); }
})();
NODE
ENDSCRIPT"""


def main() -> int:
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=120)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    sys.stdout.write(out)
    if err.strip():
        sys.stderr.write(err)
    ssh.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
