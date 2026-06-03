# 🚀 CompetitorLens — Safe Deployment Steps for sx.thetransformix.com

> **⚠️ Zero impact guarantee**: These steps will NOT touch, restart, or modify any of your existing containers. We only ADD new containers on different ports.

---

## Current Containers (DO NOT TOUCH)

```
diomedia-nginx          → ports 80, 443      (handles all HTTP/HTTPS)
diomedia-frontend       → port 8099
diomedia-backend        → port 8011
diomedia-postgres       → port 5440
quality_platform-fe     → port 9000
quality_platform-be     → port 9005
dolphin-island-app      → port 3010
qa-agent-frontend       → port 3002
qa-agent-backend        → port 4003
qa-agent-flask          → port 5004
qa-agent-postgres       → port 5056
hajj_bot                → (no exposed port)
quality-bot             → (no exposed port)
```

## New CompetitorLens Containers (NO CONFLICTS)

```
competitorlens-frontend → port 3030   ✅ no conflict
competitorlens-backend  → port 8080   ✅ no conflict
competitorlens-ai-api   → port 5050   ✅ no conflict
competitorlens-db       → port 5433   ✅ no conflict
```

---

## Step 1 — DNS Record (2 min)

Go to your DNS provider (Cloudflare / registrar) for `thetransformix.com`:

| Type | Name  | Value            | Proxy        |
|------|-------|------------------|--------------|
| A    | sx    | YOUR_VPS_IP      | DNS only ☁️  |

> **Important**: Turn OFF Cloudflare orange cloud. Use grey cloud (DNS only) so SSL works.

Verify DNS propagation:
```bash
dig sx.thetransformix.com +short
# Should return your VPS IP
```

---

## Step 2 — SSH into VPS & Clone Project (3 min)

```bash
ssh root@YOUR_VPS_IP

# Clone the project
cd /opt
git clone https://github.com/AhmedELwekel2/CompetitorLens.git competitorlens
cd /opt/competitorlens
```

---

## Step 3 — Configure Environment Files (5 min)

### 3a. Create `backend/.env`

```bash
nano /opt/competitorlens/backend/.env
```

Paste and edit these values:
```env
# Security — generate a strong random string
SECRET_KEY=change-me-to-something-random-32chars

# Azure OpenAI — fill in your actual values
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4o

# CORS origins
CORS_ORIGINS=http://localhost:3000,https://sx.thetransformix.com,http://sx.thetransformix.com

# Admin login credentials
ADMIN_EMAIL=ahmedelwekel@gmail.com
ADMIN_PASSWORD=YourSecurePassword123!
```

### 3b. Create `ai_api/.env`

```bash
nano /opt/competitorlens/ai_api/.env
```

Paste:
```env
# Azure OpenAI — same values as backend
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4o
```

---

## Step 4 — Build & Start Containers (5-10 min)

```bash
cd /opt/competitorlens

# Build and start all 4 containers in detached mode
docker compose up -d --build
```

**Verify all containers are running:**
```bash
docker compose ps
```

You should see 4 containers all with status "Up":
```
competitorlens-frontend-1   ... Up    0.0.0.0:3030->3000/tcp
competitorlens-backend-1    ... Up    0.0.0.0:8080->8000/tcp
competitorlens-ai-api-1     ... Up    0.0.0.0:5050->5000/tcp
competitorlens-db-1         ... Up    0.0.0.0:5433->5432/tcp
```

**Quick health check:**
```bash
# Test backend
curl http://localhost:8080/health
# Expected: {"status":"ok","service":"CompetitorLens API"}

# Test frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3030
# Expected: 200
```

> ✅ At this point, the app works on `http://YOUR_VPS_IP:3030` but we want it on `sx.thetransformix.com`

---

## Step 5 — Add Nginx Server Block (SAFE — no restart of existing services) (3 min)

We add a NEW server block to the existing `diomedia-nginx` container. This is **additive only** — it won't affect any existing sites.

### First, find the Docker bridge IP:

```bash
# Get the host IP that containers use to reach the host
ip route | grep docker0 | awk '{print $9}'
# Usually: 172.17.0.1
```

> Write down this IP. We'll call it `HOST_IP`. Usually `172.17.0.1`.

### Create the nginx config:

```bash
# Create a config file on the host first
cat > /tmp/competitorlens.conf << 'CONF'
server {
    listen 80;
    server_name sx.thetransformix.com;

    location / {
        proxy_pass http://172.17.0.1:3030;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support for streaming analysis
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
CONF

# ⚠️ Replace 172.17.0.1 with your actual HOST_IP if different
```

### Copy into the nginx container and reload:

```bash
# Copy the config file into the existing nginx container
docker cp /tmp/competitorlens.conf diomedia-nginx:/etc/nginx/conf.d/competitorlens.conf

# Test nginx config (this ONLY checks syntax, does NOT restart)
docker exec diomedia-nginx nginx -t
# Expected: "syntax is ok" and "test is successful"

# Reload nginx gracefully (zero downtime, existing sites unaffected)
docker exec diomedia-nginx nginx -s reload
```

### Verify it works:

```bash
# Test through nginx
curl -H "Host: sx.thetransformix.com" http://localhost
# Should return the CompetitorLens HTML page
```

> ✅ **Nothing was restarted.** Only a new config file was added and nginx was reloaded (graceful, no downtime for any existing site).

---

## Step 6 — SSL/HTTPS with Certbot (5 min)

### Get the SSL certificate:

```bash
# Temporarily stop nginx to free port 80 for certbot
docker exec diomedia-nginx nginx -s stop

# Get the certificate (standalone mode)
sudo certbot certonly --standalone -d sx.thetransformix.com --non-interactive --agree-tos -m ahmedelwekel@gmail.com

# Certificates saved at:
# /etc/letsencrypt/live/sx.thetransformix.com/fullchain.pem
# /etc/letsencrypt/live/sx.thetransformix.com/privkey.pem

# Restart the nginx container (it was stopped, not removed)
docker start diomedia-nginx
```

### Update the config to use SSL:

```bash
cat > /tmp/competitorlens.conf << 'CONF'
# HTTP → redirect to HTTPS
server {
    listen 80;
    server_name sx.thetransformix.com;
    return 301 https://$host$request_uri;
}

# HTTPS
server {
    listen 443 ssl;
    server_name sx.thetransformix.com;

    ssl_certificate /etc/nginx/ssl/sx.thetransformix.com/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/sx.thetransformix.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://172.17.0.1:3030;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
CONF
```

### Mount SSL certs into the nginx container:

You need to make the Let's Encrypt certs available inside `diomedia-nginx`. Check if the container already has volumes mounted:

```bash
docker inspect diomedia-nginx --format '{{json .Mounts}}' | python3 -m json.tool
```

**If the container already mounts `/etc/nginx/ssl`** — just copy the certs:
```bash
# Create directory inside container
docker exec diomedia-nginx mkdir -p /etc/nginx/ssl/sx.thetransformix.com

# Copy certs from host into container
docker cp /etc/letsencrypt/live/sx.thetransformix.com/fullchain.pem diomedia-nginx:/etc/nginx/ssl/sx.thetransformix.com/
docker cp /etc/letsencrypt/live/sx.thetransformix.com/privkey.pem diomedia-nginx:/etc/nginx/ssl/sx.thetransformix.com/
```

**If the container does NOT have a mount for SSL** — you'll need to recreate it with the volume. Check the `diomedia` docker-compose file and add:
```yaml
volumes:
  - /etc/letsencrypt:/etc/nginx/ssl:ro
```
Then `docker compose up -d` for the diomedia project.

### Apply the HTTPS config:

```bash
# Copy updated config
docker cp /tmp/competitorlens.conf diomedia-nginx:/etc/nginx/conf.d/competitorlens.conf

# Test and reload
docker exec diomedia-nginx nginx -t
docker exec diomedia-nginx nginx -s reload
```

### Set up auto-renewal:

```bash
# Certbot auto-renewal cron (already set up by certbot)
sudo crontab -l | { cat; echo "0 3 * * * certbot renew --quiet --deploy-hook 'docker exec diomedia-nginx nginx -s reload'"; } | sudo crontab -
```

---

## Step 7 — Final Verification (2 min)

```bash
# Test HTTPS
curl -I https://sx.thetransformix.com
# Expected: HTTP/2 200

# Test API through domain
curl https://sx.thetransformix.com/api/v1/health
# Expected: {"status":"ok","service":"CompetitorLens API","version":"1.0.0"}

# Verify existing sites still work (IMPORTANT!)
curl -I https://your-existing-diomedia-domain.com
# Expected: still 200 OK — nothing broken
```

### Open in browser:
1. Go to `https://sx.thetransformix.com`
2. Login with the admin credentials from `backend/.env`
3. Run a test analysis

---

## Summary — What Changed vs What Didn't

### ✅ NEW things created:
- 4 new Docker containers (competitorlens-*)
- 1 new nginx config file inside diomedia-nginx
- 1 DNS record (sx A record)
- 1 SSL certificate

### ❌ NOTHING changed:
- All 13 existing containers — untouched
- All existing nginx configs — untouched
- All existing ports — no conflicts
- No existing services restarted (only graceful nginx reload)

---

## Troubleshooting

| Problem | Command |
|---------|---------|
| Container won't start | `docker compose logs backend` |
| Can't reach frontend | `curl http://localhost:3030` |
| Nginx proxy not working | `docker exec diomedia-nginx nginx -t` |
| SSL cert errors | `sudo certbot certificates` |
| DNS not resolving | `dig sx.thetransformix.com` |
| Existing site broken | `docker exec diomedia-nginx cat /var/log/nginx/error.log` |
| View all container logs | `docker compose logs -f` |