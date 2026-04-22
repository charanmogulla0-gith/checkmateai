#!/usr/bin/env bash
# Stage production secrets on the Fly.io app.
#
# Reads:
#   .env                     — existing local env (ANTHROPIC_API_KEY, GITHUB_APP_*)
#   .env.fly                 — production-only cloud service creds (gitignored)
#   secrets/github-app.pem   — GitHub App private key (gitignored)
#
# Run after `flyctl launch --no-deploy` creates the app, and before `flyctl deploy`.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "ERROR: .env not found — need ANTHROPIC_API_KEY, GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET" >&2
  exit 1
fi
if [[ ! -f .env.fly ]]; then
  echo "ERROR: .env.fly not found — see .env.example for the prod cloud-service vars" >&2
  exit 1
fi
if [[ ! -f secrets/github-app.pem ]]; then
  echo "ERROR: secrets/github-app.pem not found" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
# shellcheck disable=SC1091
source .env.fly
set +a

: "${ANTHROPIC_API_KEY:?missing in .env}"
: "${GITHUB_APP_ID:?missing in .env}"
: "${GITHUB_WEBHOOK_SECRET:?missing in .env}"
: "${DATABASE_URL:?missing in .env.fly}"
: "${REDIS_URL:?missing in .env.fly}"
: "${QDRANT_URL:?missing in .env.fly}"
: "${QDRANT_API_KEY:?missing in .env.fly}"
: "${LANGFUSE_HOST:?missing in .env.fly}"
: "${LANGFUSE_PUBLIC_KEY:?missing in .env.fly}"
: "${LANGFUSE_SECRET_KEY:?missing in .env.fly}"

GITHUB_APP_PRIVATE_KEY=$(cat secrets/github-app.pem)

echo "==> Setting secrets on Fly app (this triggers one rolling restart)"
flyctl secrets set \
  ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-6}" \
  GITHUB_APP_ID="$GITHUB_APP_ID" \
  GITHUB_WEBHOOK_SECRET="$GITHUB_WEBHOOK_SECRET" \
  GITHUB_APP_PRIVATE_KEY="$GITHUB_APP_PRIVATE_KEY" \
  DATABASE_URL="$DATABASE_URL" \
  REDIS_URL="$REDIS_URL" \
  QDRANT_URL="$QDRANT_URL" \
  QDRANT_API_KEY="$QDRANT_API_KEY" \
  LANGFUSE_HOST="$LANGFUSE_HOST" \
  LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
  LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
  APP_ENV="${APP_ENV:-production}" \
  LOG_LEVEL="${LOG_LEVEL:-INFO}"

echo "==> Done. Next: flyctl deploy"
