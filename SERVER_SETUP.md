# Server Provisioning Guide

Complete guide to set up the Ubuntu cloud server (Eskiz / Azure) for production deployment.

---

## 1. Connect & Update the Server

```bash
ssh azureuser@YOUR_SERVER_IP

sudo apt update && sudo apt upgrade -y
sudo apt install -y curl wget git vim nano unzip software-properties-common
sudo timedatectl set-timezone Asia/Tashkent
```

---

## 2. Install Docker & Docker Compose

```bash
# Remove any old Docker packages
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Add Docker's official GPG key
sudo apt install -y ca-certificates curl gnupg lsb-release
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin

# Allow current user to run Docker without sudo
sudo usermod -aG docker $USER
newgrp docker

# Enable Docker on boot
sudo systemctl enable docker containerd

# Verify
docker --version
docker compose version
docker run hello-world
```

---

## 3. Configure UFW Firewall

**IMPORTANT: Allow SSH first, then enable — or you will be locked out!**

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw enable           # Type 'y' to confirm
sudo ufw status verbose
```

---

## 4. Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/taskflow.git
cd taskflow
```

---

## 5. Create the Production `.env` File

```bash
nano ~/taskflow/.env
```

Paste the following (replace ALL placeholder values):

```env
# Django
DJANGO_SECRET_KEY=generate-a-50-char-random-string-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,YOUR_SERVER_IP

# Database
DB_ENGINE=django.db.backends.postgresql
DB_NAME=taskmanager
DB_USER=taskmanager
DB_PASSWORD=choose-a-strong-database-password
DB_HOST=db
DB_PORT=5432

# Security
SECURE_SSL_REDIRECT=True

# Docker Hub (for docker-compose.prod.yml image pull)
DOCKERHUB_USERNAME=your-dockerhub-username
```

Generate a Django secret key:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## 6. Configure Nginx Domain

Edit `nginx/nginx.conf` on the server and replace `DOMAIN_PLACEHOLDER` with your real domain:

```bash
sed -i 's/DOMAIN_PLACEHOLDER/yourdomain.com/g' ~/taskflow/nginx/nginx.conf
```

---

## 7. Obtain SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot

# Get certificate in standalone mode (Nginx not running yet)
sudo certbot certonly --standalone \
    -d yourdomain.com \
    --email your-email@example.com \
    --agree-tos \
    --no-eff-email

# Verify certificate
sudo ls /etc/letsencrypt/live/yourdomain.com/

# Test auto-renewal
sudo certbot renew --dry-run
```

---

## 8. Initial Manual Deployment

```bash
cd ~/taskflow

# Pull and start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs web --tail=50
```

The `entrypoint.sh` inside the container automatically runs migrations
and collectstatic on startup.

---

## 9. Add SSH Key for GitHub Actions

Generate a dedicated deployment key on the server:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/deploy_key -N ""

# Add public key to authorized_keys
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys

# Copy the PRIVATE key (you need this for GitHub Secrets)
cat ~/.ssh/deploy_key
```

Paste the private key content as the `SSH_PRIVATE_KEY` GitHub Secret.

---

## 10. Verify End-to-End

```bash
# HTTP response
curl -I http://yourdomain.com

# HTTPS response
curl -I https://yourdomain.com

# Health check
curl https://yourdomain.com/health/
```

---

## Rollback Procedure

If a bad deployment breaks the application:

```bash
# Option A: Pull a specific image tag (from GitHub SHA)
# Edit docker-compose.prod.yml: image: username/taskflow:COMMIT_SHA
docker compose -f docker-compose.prod.yml up -d

# Option B: Git revert (triggers CI/CD to re-deploy the fix)
# (on your local machine)
git revert HEAD
git push origin main
```
