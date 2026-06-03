#!/bin/bash
# =============================================================
# CompetitorLens — Nginx + SSL Setup for sx.thetransformix.com
# =============================================================
# Run this on the VPS AFTER steps 1-4 are done (DNS + clone + env + docker compose up)
# 
# Usage:  chmod +x deploy-nginx-ssl.sh && bash deploy-nginx-ssl.sh
# =============================================================

set -e

DOMAIN="sx.thetransformix.com"
EMAIL="ahmedelwekel@gmail.com"
NGINX_CONTAINER="diomedia-nginx"
FRONTEND_PORT=3030

echo ""
echo "============================================"
echo "  CompetitorLens — Nginx & SSL Setup"
echo "  Domain: $DOMAIN"
echo "============================================"
echo ""

# ─── Step 5: Find Docker bridge IP ─────────────────────────
echo "━━━ STEP 5: Nginx Server Block ━━━"

HOST_IP=$(ip route | grep docker0 | awk '{print $9}' | head -1)
if [ -z "$HOST_IP" ]; then
    HOST_IP="172.17.0.1"
fi
echo "✓ Docker bridge IP: $HOST_IP"

# ─── Step 5: Create HTTP nginx config ──────────────────────
echo "Creating nginx config for $DOMAIN (HTTP only)..."

cat > /tmp/competitorlens.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://$HOST_IP:$FRONTEND_PORT;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE support for streaming analysis
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
EOF

echo "✓ Config file created at /tmp/competitorlens.conf"

# ─── Step 5: Copy config into nginx container ──────────────
echo "Copying config into $NGINX_CONTAINER..."

docker cp /tmp/competitorlens.conf $NGINX_CONTAINER:/etc/nginx/conf.d/competitorlens.conf

echo "✓ Config copied"

# ─── Step 5: Test nginx config ─────────────────────────────
echo "Testing nginx config..."
docker exec $NGINX_CONTAINER nginx -t

echo "✓ Nginx config is valid"

# ─── Step 5: Reload nginx gracefully ───────────────────────
echo "Reloading nginx (graceful, no downtime)..."
docker exec $NGINX_CONTAINER nginx -s reload

echo "✓ Nginx reloaded"

# ─── Step 5: Verify HTTP proxy works ───────────────────────
echo ""
echo "Testing HTTP proxy..."
sleep 2
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: $DOMAIN" http://localhost)
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
    echo "✓ HTTP proxy working! Status: $HTTP_STATUS"
else
    echo "⚠ HTTP proxy returned status $HTTP_STATUS (may need DNS first)"
fi

echo ""
echo "━━━ STEP 6: SSL Certificate ━━━"

# ─── Step 6: Check if certbot is installed ─────────────────
if ! command -v certbot &> /dev/null; then
    echo "Installing certbot..."
    apt update -qq && apt install -y -qq certbot
fi
echo "✓ Certbot available"

# ─── Step 6: Stop nginx temporarily for certbot ────────────
echo "Temporarily stopping nginx for certbot standalone mode..."
docker exec $NGINX_CONTAINER nginx -s stop
sleep 2

# ─── Step 6: Get SSL certificate ───────────────────────────
echo "Requesting SSL certificate for $DOMAIN..."
certbot certonly --standalone -d $DOMAIN --non-interactive --agree-tos -m $EMAIL

if [ $? -eq 0 ]; then
    echo "✓ SSL certificate obtained!"
else
    echo "✗ Failed to get SSL certificate. Restarting nginx and exiting..."
    docker start $NGINX_CONTAINER
    exit 1
fi

# ─── Step 6: Restart nginx container ───────────────────────
echo "Restarting nginx container..."
docker start $NGINX_CONTAINER
sleep 3

# ─── Step 6: Copy SSL certs into container ─────────────────
echo "Copying SSL certificates into container..."
docker exec $NGINX_CONTAINER mkdir -p /etc/nginx/ssl/$DOMAIN

# Check if /etc/letsencrypt exists on host
if [ -d "/etc/letsencrypt/live/$DOMAIN" ]; then
    docker cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $NGINX_CONTAINER:/etc/nginx/ssl/$DOMAIN/
    docker cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $NGINX_CONTAINER:/etc/nginx/ssl/$DOMAIN/
    echo "✓ SSL certs copied into container"
else
    echo "✗ Could not find certs at /etc/letsencrypt/live/$DOMAIN"
    exit 1
fi

# ─── Step 6: Create HTTPS nginx config ─────────────────────
echo "Creating HTTPS nginx config..."

cat > /tmp/competitorlens.conf << EOF
# HTTP → redirect to HTTPS
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

# HTTPS
server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /etc/nginx/ssl/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://$HOST_IP:$FRONTEND_PORT;
        proxy_http_version 1.1;

        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE support for streaming analysis
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
EOF

# ─── Step 6: Apply HTTPS config ────────────────────────────
echo "Applying HTTPS config..."
docker cp /tmp/competitorlens.conf $NGINX_CONTAINER:/etc/nginx/conf.d/competitorlens.conf
docker exec $NGINX_CONTAINER nginx -t
docker exec $NGINX_CONTAINER nginx -s reload

echo "✓ HTTPS config applied!"

# ─── Step 6: Set up auto-renewal ───────────────────────────
echo "Setting up SSL auto-renewal cron job..."
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec $NGINX_CONTAINER nginx -s reload'") | sort -u | crontab -
echo "✓ Auto-renewal cron set"

echo ""
echo "━━━ STEP 7: Verification ━━━"

# ─── Step 7: Test everything ───────────────────────────────
echo ""
echo "Testing HTTPS..."
sleep 2
HTTPS_STATUS=$(curl -sk -o /dev/null -w "%{http_code}" https://$DOMAIN)
echo "  https://$DOMAIN → Status: $HTTPS_STATUS"

echo "Testing API..."
API_RESPONSE=$(curl -sk https://$DOMAIN/api/v1/health 2>/dev/null || echo "failed")
echo "  https://$DOMAIN/api/v1/health → $API_RESPONSE"

echo "Testing HTTP→HTTPS redirect..."
REDIRECT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN)
echo "  http://$DOMAIN → Status: $REDIRECT_STATUS (should be 301)"

echo ""
echo "============================================"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo "============================================"
echo ""
echo "  🌐 Open: https://$DOMAIN"
echo "  📧 Admin email: $EMAIL"
echo "  🔑 Admin password: (from backend/.env)"
echo ""
echo "  If verification shows errors, check:"
echo "    - DNS: dig $DOMAIN +short"
echo "    - Logs: docker exec $NGINX_CONTAINER cat /var/log/nginx/error.log"
echo "    - Containers: cd /opt/competitorlens && docker compose ps"
echo ""