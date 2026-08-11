#!/usr/bin/env bash
set -euo pipefail

: "${HELPME_VPS_HOST:?Set the dedicated helpme.green VPS host or IP}"
: "${HELPME_VPS_USER:?Set the VPS SSH user}"
: "${HELPME_VPS_APP_DIR:?Set the remote application directory}"
: "${HELPME_VPS_ENV_FILE:?Set the pre-provisioned remote env-file path}"

image_tag="helpme.green:$(git rev-parse --short HEAD)"
remote_image="${HELPME_VPS_USER}@${HELPME_VPS_HOST}"

docker build --tag "$image_tag" .
docker save "$image_tag" | ssh "$remote_image" "docker load"
ssh "$remote_image" "test -f '$HELPME_VPS_ENV_FILE'"
ssh "$remote_image" "mkdir -p '$HELPME_VPS_APP_DIR'"
ssh "$remote_image" "docker rm --force helpme-green >/dev/null 2>&1 || true"
ssh "$remote_image" "docker run --detach --name helpme-green --restart unless-stopped --env-file '$HELPME_VPS_ENV_FILE' --publish 8080:8080 --volume '$HELPME_VPS_APP_DIR/data:/app/.data' '$image_tag'"
ssh "$remote_image" "curl --fail --silent --show-error http://127.0.0.1:8080/healthz"
