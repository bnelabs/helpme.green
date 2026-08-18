#!/usr/bin/env bash
set -euo pipefail

image_name="${HELPME_CONTAINER_IMAGE:-helpme-green:local}"
container_name="${HELPME_CONTAINER_NAME:-helpme-green-rehearsal}"
container_port="${HELPME_CONTAINER_PORT:-18084}"
access_token="${HELPME_TEST_TOKEN:-helpme-green-local-test-token}"
data_dir=$(mktemp -d)

cleanup() {
  docker rm --force "$container_name" >/dev/null 2>&1 || true
  if ! rm -rf "$data_dir" 2>/dev/null; then
    # The application deliberately runs as a non-root user, so bind-mounted
    # session files can be owned by a UID that cannot be removed by the runner.
    # Use the already-built image as a short-lived root cleanup helper.
    docker run --rm --user 0 \
      --volume "$data_dir:/app/.data" \
      "$image_name" \
      sh -c 'rm -rf /app/.data/* /app/.data/.[!.]* /app/.data/..?*' \
      >/dev/null 2>&1 || true
    rmdir "$data_dir" 2>/dev/null || true
  fi
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
  --env "HELPME_ACCESS_TOKEN=$access_token" \
  --env "HELPME_MASTER_KEY=$master_key" \
  --env "HELPME_AI_ENABLED=0" \
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
  --header "Authorization: Bearer $access_token" \
  --header "Content-Type: application/json" \
  --data '{}' \
  "http://127.0.0.1:$container_port/api/sessions")
session_id=$(python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])' <<<"$created")

message_response=$(curl --fail --silent --show-error --max-time 5 \
  --request POST \
  --header "Authorization: Bearer $access_token" \
  --header "Content-Type: application/json" \
  --data '{"message":"I have rubber"}' \
  "http://127.0.0.1:$container_port/api/sessions/$session_id/message")

docker restart "$container_name" >/dev/null
wait_for_health "$health_after"
resumed=$(curl --fail --silent --show-error --max-time 5 \
  --header "Authorization: Bearer $access_token" \
  "http://127.0.0.1:$container_port/api/sessions/$session_id")

python3 -c '
import json
import sys

message = json.loads(sys.argv[1])
resumed = json.loads(sys.argv[2])
health = json.load(open(sys.argv[3], encoding="utf-8"))
assert message["error"] is None
assert message["data"]["ai_used"] is False
assert health["status"] == "ok" and health["audit_chain_valid"]
assert "topic" in resumed["session"] and "material" not in resumed["session"]
print(json.dumps({
    "health_after_restart": health,
    "session_resumed": True,
    "natural_message_endpoint": True,
}))
' "$message_response" "$resumed" "$health_after"
