#!/bin/bash
# SSL Certificate Renewal Script
# Run this script on the server: bash renew_ssl_certificate.sh

set -e

echo "========================================"
echo "SSL Certificate Renewal"
echo "========================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

# Step 1: Fix certbot installation if needed
echo "[1/5] Checking certbot installation..."
if ! command -v certbot &> /dev/null; then
    echo "Certbot not found, installing..."
    apt-get update
    apt-get install -y certbot python3-certbot-nginx
elif certbot --version 2>&1 | grep -q "snap.*missing"; then
    echo "Snap certbot is broken, fixing..."
    snap remove certbot 2>&1 || true
    snap install --classic certbot 2>&1 || {
        echo "Snap install failed, using apt instead..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    }
fi

echo "[OK] Certbot is available"
certbot --version

# Step 2: Check certificate expiration
echo
echo "[2/5] Checking certificate expiration..."
if [ -f "/etc/letsencrypt/live/masternoder.dk/cert.pem" ]; then
    openssl x509 -enddate -noout -in /etc/letsencrypt/live/masternoder.dk/cert.pem
else
    echo "Certificate file not found!"
    exit 1
fi

# Step 3: Test nginx config
echo
echo "[3/5] Testing nginx configuration..."
if nginx -t; then
    echo "[OK] Nginx config is valid"
else
    echo "[ERROR] Nginx config has errors!"
    exit 1
fi

# Step 4: Renew certificate
echo
echo "[4/5] Renewing SSL certificate..."
echo "Running: certbot renew --non-interactive"

if certbot renew --non-interactive; then
    echo "[OK] Certificate renewal completed"
else
    echo "[WARN] Standard renewal failed, trying force renewal..."
    if certbot certonly --nginx --force-renewal -d masternoder.dk -d www.masternoder.dk --non-interactive --agree-tos; then
        echo "[OK] Force renewal succeeded"
    else
        echo "[ERROR] Certificate renewal failed!"
        exit 1
    fi
fi

# Step 5: Reload nginx
echo
echo "[5/5] Reloading nginx..."
if systemctl reload nginx; then
    echo "[OK] Nginx reloaded successfully"
else
    echo "[WARN] Reload failed, trying restart..."
    systemctl restart nginx
    echo "[OK] Nginx restarted"
fi

# Verify new expiration
echo
echo "Verifying new certificate expiration..."
openssl x509 -enddate -noout -in /etc/letsencrypt/live/masternoder.dk/cert.pem

echo
echo "========================================"
echo "Certificate renewal complete!"
echo "========================================"
echo
echo "Test your site: https://masternoder.dk"
echo
