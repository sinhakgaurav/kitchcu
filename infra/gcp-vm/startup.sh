#!/bin/bash
# kitchCU - GCE VM startup script (Ubuntu 22.04). Runs as root on every boot.
# Secrets are read from instance metadata (set once at `gcloud compute instances create`
# via --metadata=...), never baked into this script or the git repo.
set -euo pipefail
exec > >(tee -a /var/log/ckac-startup.log) 2>&1
echo "=== ckac startup: $(date -u) ==="

REPO_DIR=/opt/ckac
REPO_URL="https://github.com/sinhakgaurav/kitchcu.git"
meta() { curl -sf -H "Metadata-Flavor: Google" "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1" || true; }

# --- 1. Swap file safety net (e2-small = 2GB RAM, ~20 containers) -----------------
if [ ! -f /swapfile ]; then
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo "/swapfile none swap sw 0 0" >> /etc/fstab
  sysctl -w vm.swappiness=10
fi

# --- 2. Docker Engine + Compose plugin + git ---------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -y
  apt-get install -y ca-certificates curl gnupg git python3
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  systemctl enable --now docker
fi

# --- 3. Fetch code -------------------------------------------------------------------
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" fetch origin main
  git -C "$REPO_DIR" reset --hard origin/main
else
  git clone --depth 1 --branch main "$REPO_URL" "$REPO_DIR"
fi

# --- 4. Write production .env from instance metadata ---------------------------------
ENV_DIR="$REPO_DIR/infra/gcp-vm"
MEDIA_BACKEND="$(meta media-backend)"
MEDIA_BACKEND="${MEDIA_BACKEND:-minio}"

if [ "$MEDIA_BACKEND" = "gcs" ]; then
  MINIO_ENDPOINT="storage.googleapis.com"
  MINIO_SECURE="true"
  MINIO_PUBLIC_URL="https://storage.googleapis.com"
  MINIO_ACCESS_KEY="$(meta minio-access-key)"
  MINIO_SECRET_KEY="$(meta minio-secret-key)"
  MINIO_BUCKET="$(meta minio-bucket)"
else
  # Default: local MinIO container (use when GCS HMAC creation is org-policy blocked).
  MINIO_ENDPOINT="minio:9000"
  MINIO_SECURE="false"
  MINIO_PUBLIC_URL="https://media.kitchcu.com"
  MINIO_ACCESS_KEY="$(meta minio-access-key)"
  MINIO_SECRET_KEY="$(meta minio-secret-key)"
  MINIO_ACCESS_KEY="${MINIO_ACCESS_KEY:-ckac}"
  MINIO_SECRET_KEY="${MINIO_SECRET_KEY:-ckac_minio_dev}"
  MINIO_BUCKET="$(meta minio-bucket)"
  MINIO_BUCKET="${MINIO_BUCKET:-ckac-media}"
fi

cat > "$ENV_DIR/.env" <<EOF
POSTGRES_USER=ckac
POSTGRES_PASSWORD=$(meta db-password)
POSTGRES_DB=ckac

APP_ENV=production
CORS_ORIGINS=https://kitchcu.com,https://www.kitchcu.com,https://customer.kitchcu.com,https://kitchen.kitchcu.com,https://admin.kitchcu.com,https://api.kitchcu.com

JWT_SECRET=$(meta jwt-secret)
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_MINUTES=480
JWT_REFRESH_EXPIRE_DAYS=7

INTERNAL_API_KEY=$(meta internal-api-key)
WHATSAPP_VERIFY_TOKEN=$(meta whatsapp-verify-token)

ADMIN_EMAIL=admin@kitchcu.com
ADMIN_PASSWORD=$(meta admin-password)

MEDIA_STORAGE_BACKEND=minio
MINIO_ENDPOINT=${MINIO_ENDPOINT}
MINIO_SECURE=${MINIO_SECURE}
MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
MINIO_BUCKET=${MINIO_BUCKET}
MINIO_PUBLIC_URL=${MINIO_PUBLIC_URL}

CUSTOMER_OAUTH_REDIRECT_BASE=https://customer.kitchcu.com
EOF
chmod 600 "$ENV_DIR/.env"

# --- 5. Build + start the full stack (idempotent - safe on every reboot) -------------
cd "$REPO_DIR"
docker compose -f infra/gcp-vm/docker-compose.prod.yml --env-file infra/gcp-vm/.env up -d --build

echo "=== ckac startup done: $(date -u) ==="
