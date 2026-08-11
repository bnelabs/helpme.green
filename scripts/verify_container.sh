#!/usr/bin/env bash
set -euo pipefail

image_name="${HELPME_CONTAINER_IMAGE:-helpme-green:phase-a}"
container_name="${HELPME_CONTAINER_NAME:-helpme-green-rehearsal}"
container_port="${HELPME_CONTAINER_PORT:-18084}"
console_token="${HELPME_TEST_TOKEN:-helpme-green-local-test-token}"
data_dir=$(mktemp -d)

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  rm -rf "$data_dir"
}
trap cleanup EXIT

chmod 777 "$data_dir"
docker build --tag "$image_name" .
master_key=$(docker run --rm "$image_name" python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')
docker rm --force "$container_name" >/dev/null 2>&1 || true
docker run --detach \
  --name "$container_name" \
  --publish "$container_port:8080" \
  --volume "$data_dir:/app/.data" \
  --env "HELPME_CONSOLE_TOKEN=$console_token" \
  --env "HELPME_MASTER_KEY=$master_key" \
  "$image_name" >/dev/null

wait_for_health() {
  local health_path="$1"
  local attempt
  for attempt in $(seq 1 30); do
    if curl --fail --silent --show-error --max-time 2 \
      "http://127.0.0.1:$container_port/healthz" >"$health_path" 2>/dev/null; then
      return 0
    fi
    sleep 1
  done
  docker logs "$container_name" >&2
  return 1
}

health_before=$(mktemp)
health_after=$(mktemp)
trap 'rm -f "$health_before" "$health_after"; cleanup' EXIT
wait_for_health "$health_before"

created=$(curl --fail --silent --show-error --max-time 5 \
  --request POST \
  --header "Authorization: Bearer $console_token" \
  --header "Content-Type: application/json" \
  --data '{"material":"copper cable","geography":"Bulgaria / EU"}' \
  "http://127.0.0.1:$container_port/api/sessions")
session_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' <<<"$created")

answer_response=$(curl --fail --silent --show-error --max-time 5 \
  --request POST \
  --header "Authorization: Bearer $console_token" \
  --header "Content-Type: application/json" \
  --data '{"command":"/answer contamination unknown"}' \
  "http://127.0.0.1:$container_port/api/sessions/$session_id/command")
snapshot_response=$(curl --fail --silent --show-error --max-time 5 \
  --request POST \
  --header "Authorization: Bearer $console_token" \
  --header "Content-Type: application/json" \
  --data '{"command":"/snapshot"}' \
  "http://127.0.0.1:$container_port/api/sessions/$session_id/command")

docker restart "$container_name" >/dev/null
wait_for_health "$health_after"
resumed=$(curl --fail --silent --show-error --max-time 5 \
  --header "Authorization: Bearer $console_token" \
  "http://127.0.0.1:$container_port/api/sessions/$session_id")

python3 -c '
import json
import sys

answer = json.loads(sys.argv[1])
snapshot = json.loads(sys.argv[2])
health = json.load(open(sys.argv[3], encoding="utf-8"))
resumed = json.loads(sys.argv[4])
assert answer["error"] is None
assert snapshot["error"] is None and snapshot["data"]["snapshot_id"]
assert health["status"] == "ok" and health["audit_chain_valid"]
assert resumed["session"]["facts"]["contamination"]["label"] == "unknown"
print(json.dumps({
    "health_after_restart": health,
    "session_resumed": True,
    "snapshot_created": True,
    "fact_label": "unknown",
}))
' "$answer_response" "$snapshot_response" "$health_after" "$resumed"
