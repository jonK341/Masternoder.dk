# SSL Certificate Renewal Guide

Your SSL certificate for masternoder.dk has expired (Feb 16, 2026). Here are several ways to renew it:

## Option 1: Use the Python Script (Recommended)

Run the automated script:
```bash
python scripts/renew_ssl_certificate.py
```

## Option 2: SSH into Server and Run Commands Manually

If the script fails, SSH into your server and run these commands:

### Step 1: Fix Certbot Installation

```bash
# Remove broken snap certbot
snap remove certbot 2>&1 || true

# Install certbot via apt
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Fix Python dependencies if needed
apt-get install -y --reinstall python3-pyopenssl python3-cryptography python3-openssl
pip3 install --upgrade --force-reinstall pyopenssl cryptography
```

### Step 2: Renew Certificate

```bash
# Try standard renewal
certbot renew --non-interactive

# If that fails, force renewal
certbot certonly --nginx --force-renewal -d masternoder.dk -d www.masternoder.dk --non-interactive --agree-tos
```

### Step 3: Reload Nginx

```bash
nginx -t  # Test config
systemctl reload nginx
```

### Step 4: Verify

```bash
openssl x509 -enddate -noout -in /etc/letsencrypt/live/masternoder.dk/cert.pem
```

## Option 3: Use the Bash Script on Server

1. Upload `scripts/renew_ssl_certificate.sh` to your server
2. Make it executable: `chmod +x renew_ssl_certificate.sh`
3. Run as root: `sudo bash renew_ssl_certificate.sh`

## Option 4: Fix Certbot Dependencies First

If certbot has Python dependency issues, fix them first:

```bash
# On the server, run:
apt-get update
apt-get install -y --reinstall python3-certbot python3-certbot-nginx python3-pyopenssl python3-cryptography python3-openssl

# Or upgrade via pip
pip3 install --upgrade --force-reinstall certbot pyopenssl cryptography

# Then try renewal
certbot renew --non-interactive
```

## Troubleshooting

### If certbot still fails with OpenSSL errors:

```bash
# Remove and reinstall certbot completely
apt-get remove --purge certbot python3-certbot-nginx
apt-get autoremove
apt-get update
apt-get install -y certbot python3-certbot-nginx

# Or use snap (if apt version is broken)
snap remove certbot
snap install --classic certbot
```

### Check certificate status:

```bash
certbot certificates
```

### Test renewal without actually renewing:

```bash
certbot renew --dry-run
```

## Auto-Renewal Setup

After fixing the certificate, ensure auto-renewal is working:

```bash
# Test auto-renewal
certbot renew --dry-run

# Check if certbot timer is active
systemctl status certbot.timer
systemctl enable certbot.timer
```

## Quick Fix (If Everything Else Fails)

If certbot is completely broken, you can temporarily disable SSL and re-enable it:

1. Comment out SSL in nginx config temporarily
2. Reload nginx
3. Run: `certbot --nginx -d masternoder.dk -d www.masternoder.dk --non-interactive --agree-tos`
4. Uncomment SSL in nginx config
5. Reload nginx
