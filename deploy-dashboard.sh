#!/usr/bin/env bash
# Pull the pushed branch on the NUC and rebuild only the dashboard container.
# Never hangs: ssh fails fast instead of prompting, and the whole run is capped.
#   ./deploy-dashboard.sh            (default limit 600s)
#   DEPLOY_TIMEOUT=900 ./deploy-dashboard.sh
set -u
HOST=${DEPLOY_HOST:-nuc12}
LIMIT=${DEPLOY_TIMEOUT:-600}
DIR=/home/dlavoie/Documents/sunset-code
COMPOSE="docker compose -f docker-compose.existing-infra.yml"

timeout --kill-after=10 "$LIMIT" ssh -o BatchMode=yes -o ConnectTimeout=15 \
  -o ServerAliveInterval=15 -o ServerAliveCountMax=4 "$HOST" \
  "set -e; cd $DIR; git pull --ff-only -q; git log --oneline -1;
   $COMPOSE up -d --build --quiet-pull dashboard </dev/null;
   docker ps --filter name=dashboard --format '{{.Names}} {{.Status}}'"
rc=$?
case $rc in
  0)   echo "deploy ok" ;;
  124|137) echo "deploy FAILED: no finish within ${LIMIT}s (ssh stuck, e.g. Tailscale SSH waiting on a check-mode approval, or a slow build)" >&2 ;;
  255) echo "deploy FAILED: ssh to $HOST could not connect or log in without a prompt" >&2 ;;
  *)   echo "deploy FAILED: remote command exited $rc" >&2 ;;
esac
exit $rc
