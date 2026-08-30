#!/usr/bin/env bash
# Wrapper for the LangFuse + checkpointer stack.
#
# Exists so the two -f flags and --env-file are not retyped (or misremembered):
# invoking `docker compose` on the vendored file *alone* republishes upstream's
# 5432/6379 bindings and collides with the host services.
#
#   ./scripts/stack.sh up          # start detached
#   ./scripts/stack.sh down        # stop, keep volumes
#   ./scripts/stack.sh logs -f     # follow
#   ./scripts/stack.sh ps
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -f .env ]]; then
  echo "error: .env not found — run: cp .env.example .env, then fill in the secrets" >&2
  exit 1
fi

CMD=("docker" "compose" "--env-file" ".env"
     "-f" "docker/docker-compose.yml"
     "-f" "docker/docker-compose.override.yml")

case "${1:-}" in
  up)   shift; exec "${CMD[@]}" up -d "$@" ;;
  *)    exec "${CMD[@]}" "$@" ;;
esac
