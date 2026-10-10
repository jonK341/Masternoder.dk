import os, sys
sys.path.insert(0, '/var/www/html')
os.chdir('/var/www/html')
for line in open('.env', encoding='utf-8', errors='replace'):
    line = line.strip()
    if not line or line.startswith('#') or '=' not in line: continue
    k, v = line.split('=', 1)
    k, v = k.strip(), v.strip().strip('"').strip("'")
    if k and k not in os.environ: os.environ[k] = v
import scripts.remote_vault_import as _
from backend.services import exchange_secrets_vault_service as vault
from backend.services.exchange_venue_api_service import venue_has_credentials
names = vault.list_secret_names()
print('import_ok', 'xeggex' in open('/dev/null','w') or True)
print('xeggex_in_vault', 'xeggex_api_key' in names and 'xeggex_api_secret' in names)
print('venue_has_credentials', venue_has_credentials('xeggex'))
