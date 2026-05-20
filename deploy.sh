#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/root/trading_platform}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.server.yml}"
DEPLOY_BRANCH="${DEPLOY_BRANCH:-main}"

cd "$APP_DIR"

if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Missing $COMPOSE_FILE in $APP_DIR"
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "Missing .env in $APP_DIR"
  exit 1
fi

if [ ! -f "back/config/auth/firebase-service-account.json" ]; then
  echo "Missing back/config/auth/firebase-service-account.json"
  exit 1
fi

if ! grep -q '^NGROK_AUTHTOKEN=' .env && [ -z "${NGROK_AUTHTOKEN:-}" ]; then
  echo "Missing NGROK_AUTHTOKEN in .env or environment"
  exit 1
fi

echo "Updating repository from origin/${DEPLOY_BRANCH}..."
git fetch origin "$DEPLOY_BRANCH"
git reset --hard "origin/${DEPLOY_BRANCH}"

echo "Pulling backend image..."
docker compose -f "$COMPOSE_FILE" pull back || echo "Backend image pull failed; continuing with any existing local image"

echo "Stopping existing compose services..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans || true

echo "Freeing containers that still publish port 8000..."
PORT_8000_CONTAINERS="$(docker ps --format '{{.ID}} {{.Ports}}' | awk '/127\.0\.0\.1:8000|0\.0\.0\.0:8000|:8000->/ {print $1}')"
if [ -n "$PORT_8000_CONTAINERS" ]; then
  docker stop $PORT_8000_CONTAINERS
  docker rm $PORT_8000_CONTAINERS
fi

echo "Starting services..."
docker compose -f "$COMPOSE_FILE" up -d --build --remove-orphans

docker compose -f "$COMPOSE_FILE" ps
