import os, sys
sys.path.insert(0, '/var/www/html'); os.chdir('/var/www/html')
for line in open('.env'):
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k, v = line.split('=', 1)
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k and k not in os.environ: os.environ[k] = v
from backend.services.exchange_venue_api_service import venue_has_credentials, get_account_balance
from backend.services.external_exchange_connector_service import fetch_ticker
print('venue_has_credentials', venue_has_credentials('xeggex'))
t = fetch_ticker('xeggex', 'DOGE')
print('ticker_ok', bool(t.get('bid') or t.get('last')))
bal = get_account_balance('xeggex', dry_run=False)
print('account_api', {'ok': bal.get('success'), 'status': bal.get('status_code'), 'err': bal.get('error')})
