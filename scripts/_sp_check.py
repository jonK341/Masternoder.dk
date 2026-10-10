import json, sys
sys.path.insert(0, '/var/www/html')
from backend.services.exchange_sales_pool_service import sales_pool_status
d = sales_pool_status()
for k in ('transfer_count', 'last_transfer_at', 'last_tick', 'pool_gaps'):
    if k in d:
        print(k, d.get(k))
