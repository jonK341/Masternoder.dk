#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from deploy_ssh_env import connect_deploy_ssh

REMOTE = r"""bash -s <<'ENDSCRIPT'
set +e
cd /var/www/explorer

echo '== mongo richlist via node db module =='
node - <<'NODE'
const db=require('./lib/database');
const settings=require('./lib/settings');
settings.reload(function(){
  db.connect(function(){
    db.check_richlist(settings.coin.name, function(exists){
      console.log('richlist_exists', exists);
      db.get_richlist(settings.coin.name, function(rl){
        if(!rl){ console.log('get_richlist null'); process.exit(0); }
        const bal=(rl.balance||[]).slice(0,3);
        console.log('balance_top3', JSON.stringify(bal));
        process.exit(0);
      });
    });
  });
});
NODE

echo '== run reindex-rich (120s) =='
timeout 120 node scripts/sync.js reindex-rich 2>&1 | tail -30

echo '== mongo richlist after reindex =='
node - <<'NODE'
const db=require('./lib/database');
const settings=require('./lib/settings');
settings.reload(function(){
  db.connect(function(){
    db.get_richlist(settings.coin.name, function(rl){
      if(!rl){ console.log('get_richlist null'); process.exit(0); }
      console.log('balance_count', (rl.balance||[]).length);
      console.log('balance_top1', JSON.stringify((rl.balance||[])[0]));
      process.exit(0);
    });
  });
});
NODE

echo '== grep ext routes file =='
ls routes/
grep -n "router\|getrich\|getdistribution" routes/ext.js 2>/dev/null | head -30
grep -n "getrich\|getdistribution" routes/*.js 2>/dev/null | head -30
ENDSCRIPT"""

def main():
    ssh, auth, _ = connect_deploy_ssh()
    print(f"Connected ({auth})\n")
    _, stdout, stderr = ssh.exec_command(REMOTE, timeout=150)
    sys.stdout.buffer.write(stdout.read())
    err = stderr.read().decode()
    if err.strip(): print(err, file=sys.stderr)
    ssh.close()

if __name__ == "__main__":
    main()
