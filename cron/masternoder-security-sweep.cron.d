# Masternoder security sweep — every 30 minutes
*/30 * * * * root MN2_CRON_HOST=http://127.0.0.1:5000 /var/www/html/cron/security_sweep.sh >/dev/null 2>&1
