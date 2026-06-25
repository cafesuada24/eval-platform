#!/bin/bash
# GCP GCE Startup Script
set -e

echo "=== System Update and Dependencies ==="
apt-get update && apt-get upgrade -y
apt-get install -y curl git apt-transport-https ca-certificates gnupg lsb-release

# Install Docker Engine
echo "=== Installing Docker ==="
mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Query GCP Metadata Server for application secrets
echo "=== Loading Secrets from Metadata Server ==="
METADATA_URL="http://metadata.google.internal/computeMetadata/v1/instance/attributes"
GOOGLE_API_KEY=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/google_api_key")
CLOUDFLARE_TUNNEL_TOKEN=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/cloudflare_tunnel_token")
NEXT_PUBLIC_API_URL=$(curl -H "Metadata-Flavor: Google" "$METADATA_URL/next_public_api_url")

# Setup App Directory
cd /home/ubuntu
if [ ! -d "eval-platform" ]; then
  echo "=== Cloning Repository ==="
  git clone https://github.com/your-username/eval-platform.git
fi
cd eval-platform

# Generate Production .env File
echo "=== Creating .env ==="
cat <<EOF > .env
GOOGLE_API_KEY=$GOOGLE_API_KEY
CLOUDFLARE_TUNNEL_TOKEN=$CLOUDFLARE_TUNNEL_TOKEN
NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
EOF
chmod 600 .env

# Create Database Volume Path
mkdir -p data/fixtures
chown -R ubuntu:ubuntu /home/ubuntu/eval-platform

# Spin Up Containers
echo "=== Launching Docker Compose Workloads ==="
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d

echo "=== Deployment Successfully Completed ==="
