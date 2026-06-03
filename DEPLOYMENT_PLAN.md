# 🚀 CompetitorLens — Deployment Plan for sx.thetransformix.com

## Architecture Overview

```
Internet → sx.thetransformix.com (DNS → VPS IP)
         → Existing Nginx (port 80/443) [SSL termination]
              → proxy_pass http://localhost:3030
                   → CompetitorLens Frontend (Next.js :3030→3000)
                        → /api/v1/* proxied to Backend (FastAPI :8080→8000)
                             → Backend → PostgreSQL (:5433→5432)
                             → Backend → AI API (Flask :5050→5000)
```

### Services Summary

| Service       | Internal Port | Host Port | Image/Tech               |
|---------------|---------------|-----------|--------------------------|
| frontend      | 3000          | 3030      | Next.js (Node 20 Alpine) |
| backend       | 8000          | 8080      | FastAPI (Python 3.12)    |
| ai-api        | 5000          | 5050      | Flask/Gunicorn + Chrome  |
| db            | 5432          | 5433      | PostgreSQL 16 Alpine     |

---

## Step 1: DNS Configuration

In your domain registrar / Cloudflare dashboard for `thetransformix.com`:

```
Type: A
Name: sx
Value: <YOUR_VPS_IP_ADDRESS>
TTL: 300 (or Auto)
Proxy: DNS only (grey cloud) — NOT proxied through Cloudflare
```

> ⚠️ **Important**: Turn OFF the Cloudflare proxy (orange cloud) for this subdomain. 
> Use DNS-only mode (grey cloud) so SSL certificates work properly with Certbot.

---

## Step 2: Prepare the VPS

SSH into your VPS and install prerequisites (if not already installed):

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker & Docker Compose (if not installed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Certbot for SSL
sudo apt install -y certbot

# Install nginx utility tools
sudo apt install -y nginx
```

---

## Step 3: Clone & Configure the Project on VPS

```bash
# Clone the repository
cd /opt
git clone https://github.com/AhmedELwekel2/CompetitorLens.git competitorlens
cd competitorlens

# Copy and edit backend environment
cp backend/.env.example backend/.env
nano backend/.env
```

### `backend/.env` — Fill in these values:

```env
# These are set by docker-compose, but you can keep them as fallback
SECRET_KEY=<generate-a-strong-random-string>

# Azure OpenAI (REQUIRED for AI analysis)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4o

# CORS (the domain where the app will be accessed)
CORS_ORIGINS=http://localhost:3000,https://sx.thetransformix.com,https://sx.thetransformix.com/api/v1

# Admin credentials
ADMIN_EMAIL=ahmedelwekel@gmail.com
ADMIN_PASSWORD=<your-secure-password>
```

### `ai_api/.env` — Fill in these values:

```env
# Azure OpenAI (same as backend)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_MODEL=gpt-4o
```

---

## Step 4: Build & Start Containers

```bash
cd /opt/competitorlens

# Build and start all services
docker compose up -d --build

# Watch logs to verify startup
docker compose logs -f
```

Wait until you see:
- `✅ Admin user created: ahmedelwekel@gmail.com` (first time only)
- Backend health check passing
- All containers running

---

## Step 5: Configure Nginx Reverse Proxy

Since your VPS already has an nginx container (`diomedia-nginx`) on ports 80/443, you have two options:

### Option A: Use the Existing diomedia-nginx (RECOMMENDED)

Add a server block to the existing nginx config:

```bash
# Find the nginx config directory for diomedia
docker exec diomedia-nginx ls /etc/nginx/conf.d/

# Create a config file for our app
docker exec diomedia-nginx sh -c 'cat > /etc/nginx/conf.d/competitorlens.conf << "EOF"
# CompetitorLens - sx.thetransformix.com
server {
    listen 80;
    server_name sx.thetransformix.com;

    # Redirect HTTP to HTTPS (uncomment after SSL setup)
    # return 301 https://$host$request_uri;

    # --- Uncomment this block for HTTP (before SSL), comment the return above ---
    location / {
        proxy_pass http://host.docker.internal:3030;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support (for streaming analysis)
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
EOF'

# Reload nginx
docker exec diomedia-nginx nginx -t && docker exec diomedia-nginx nginx -s reload
```

**Note**: If `host.docker.internal` doesn't resolve, use the host's actual IP or Docker bridge IP:
```bash
# Get the Docker bridge IP
ip addr show docker0 | grep inet
# Usually 172.17.0.1 — replace host.docker.internal with this IP
```

### Option B: Use Host's Native Nginx

If the existing nginx container can't easily proxy to your containers, use the host nginx:

```bash
# Stop host nginx if running
sudo systemctl stop nginx

# Or use a different approach — create a config
sudo tee /etc/nginx/sites-available/sx.thetransformix.com << 'EOF'
server {
    listen 80;
    server_name sx.thetransformix.com;

    location / {
        proxy_pass http://127.0.0.1:3030;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/sx.thetransformix.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl start nginx
```

---

## Step 6: SSL Certificate (HTTPS) with Certbot

### If using the diomedia-nginx container:

```bash
# Get SSL cert using Certbot standalone mode
sudo certbot certonly --standalone -d sx.thetransformix.com --non-interactive --agree-tos -m ahmedelwekel@gmail.com

# Certificates will be saved to:
# /etc/letsencrypt/live/sx.thetransformix.com/fullchain.pem
# /etc/letsencrypt/live/sx.thetransformix.com/privkey.pem

# Copy certs into the container's volume or mount them
# Find where diomedia-nginx mounts its config:
docker inspect diomedia-nginx | grep -A5 Mounts

# Update the nginx config to add SSL:
docker exec diomedia-nginx sh -c 'cat > /etc/nginx/conf.d/competitorlens.conf << "EOF"
server {
    listen 80;
    server_name sx.thetransformix.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name sx.thetransformix.com;

    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://host.docker.internal:3030;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding on;
    }
}
EOF'

# Reload nginx
docker exec diomedia-nginx nginx -t && docker exec diomedia-nginx nginx -s reload
```

### If using host's native Nginx:

```bash
# Install certbot nginx plugin
sudo apt install -y python3-certbot-nginx

# Get and install SSL certificate automatically
sudo certbot --nginx -d sx.thetransformix.com --non-interactive --agree-tos -m ahmedelwekel@gmail.com

# Certbot will automatically modify the nginx config to add SSL
# Auto-renewal is set up via systemd timer
sudo systemctl enable certbot.timer
```

---

## Step 7: Verify Everything Works

```bash
# 1. Check all containers are running
docker compose ps

# 2. Test backend health directly
curl http://localhost:8080/health
# Expected: {"status":"ok","service":"CompetitorLens API"}

# 3. Test frontend directly
curl -I http://localhost:3030
# Expected: HTTP/1.1 200 OK

# 4. Test through domain (after DNS propagation)
curl -I http://sx.thetransformix.com
# Expected: HTTP/1.1 301 (redirect to HTTPS)

curl -I https://sx.thetransformix.com
# Expected: HTTP/2 200

# 5. Test API through domain
curl https://sx.thetransformix.com/api/v1/health
# Expected: {"status":"ok","service":"CompetitorLens API","version":"1.0.0"}
```

---

## Step 8: Open the App in Browser

1. Navigate to `https://sx.thetransformix.com`
2. Login with admin credentials:
   - Email: `ahmedelwekel@gmail.com`
   - Password: (what you set in `backend/.env`)
3. Test a Market Analysis or Business Analysis

---

## Port Conflict Check

Your VPS already uses these ports — our setup avoids ALL conflicts:

| Existing Service          | Port Used | Our Service | Our Port | Conflict? |
|---------------------------|-----------|-------------|----------|-----------|
| diomedia-nginx            | 80, 443   | (shared)    | —        | ✅ No     |
| quality_platform-frontend | 9000      | frontend    | 3030     | ✅ No     |
| quality_platform-backend  | 9005      | backend     | 8080     | ✅ No     |
| dolphin-island-app        | 3010      | —           | —        | ✅ No     |
| qa-agent-frontend         | 3002      | —           | —        | ✅ No     |
| qa-agent-backend          | 4003      | —           | —        | ✅ No     |
| qa-agent-flask            | 5004      | ai-api      | 5050     | ✅ No     |
| qa-agent-postgres         | 5056      | db          | 5433     | ✅ No     |
| diomedia-backend          | 8011      | —           | —        | ✅ No     |
| diomedia-frontend         | 8099      | —           | —        | ✅ No     |
| diomedia-postgres         | 5440      | —           | —        | ✅ No     |

---

## Troubleshooting

### Container won't start
```bash
docker compose logs <service-name>
# e.g., docker compose logs backend
```

### Frontend can't reach backend
- Verify `BACKEND_URL=http://backend:8000` in docker-compose (Docker internal DNS)
- Verify `NEXT_PUBLIC_API_URL` is set correctly
- Check CORS origins in `backend/.env`

### SSL issues
```bash
# Check certbot logs
sudo certbot certificates

# Renew manually
sudo certbot renew --force-renewal
```

### Database connection issues
```bash
# Check if DB is ready
docker compose exec db pg_isready -U competitorlens

# Connect to DB directly
docker compose exec db psql -U competitorlens -d competitorlens
```

### Nginx not proxying correctly
```bash
# Test nginx config
docker exec diomedia-nginx nginx -t

# Check nginx error logs
docker exec diomedia-nginx cat /var/log/nginx/error.log

# Or with host nginx:
sudo nginx -t
sudo tail -f /var/log/nginx/error.log
```

---

## Updating the App

```bash
cd /opt/competitorlens

# Pull latest code
git pull origin main

# Rebuild and restart (zero downtime)
docker compose up -d --build

# If database migrations needed:
docker compose exec backend alembic upgrade head
```

---

## Files Modified for This Deployment

The following files have been updated for production deployment:

1. **`docker-compose.yml`** — Changed host ports to avoid conflicts (3030, 8080, 5050, 5433)
2. **`docker-compose.yml`** — Added production environment variables for the domain
3. **`backend/config.py`** — Added `https://sx.thetransformix.com` to CORS origins
4. **`nginx/sx.thetransformix.com.conf`** — New nginx reverse proxy config file (reference)