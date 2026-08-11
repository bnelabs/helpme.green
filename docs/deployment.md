# Deployment and runtime boundaries

helpme.green is designed local-first. The supported short-term deployment is Docker Compose on the
operator’s machine, with an optional dedicated VPS deployment kept separate from business systems.
The application must not receive Konverta operational credentials or user data unless that boundary
has been deliberately designed and reviewed.

## Local Docker

Docker Compose exposes the web app only on `127.0.0.1:8080`. The container persists sessions, audit
history, the runtime knowledge database, and raw source downloads in the named `helpme_data` volume.
The Precious Plastic kit is mounted read-only.

Create the required encryption key in the current shell and start the app:

```bash
export HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:muse-glimmer-30B'
export HELPME_LOCALAI_BASE_URL='http://192.168.68.57:8090/v1'
docker compose up -d --build
curl http://127.0.0.1:8080/healthz
```

`HELPME_MASTER_KEY` protects encrypted local BYOK storage. It is not a browser login token.
`HELPME_CONSOLE_TOKEN` is optional. Leave it unset for a local no-token browser; set it only when a
token gate is wanted:

```bash
export HELPME_CONSOLE_TOKEN='local-development-only-token'
```

When the token is configured, open [http://localhost:8080](http://localhost:8080), enter the token,
and click Connect. When it is not configured, the browser should open the conversation surface
directly. Do not paste an OpenRouter or LocalAI provider key into this browser field.

Check runtime state:

```bash
docker compose ps
docker compose logs --no-color --tail=200 helpme-green
curl http://127.0.0.1:8080/healthz
```

## Populate the Docker knowledge volume

The host digest and the Docker digest are separate databases. Run this to populate the container’s
runtime copy:

```bash
docker compose run --rm helpme-green \
  python -m helpme_green.knowledge_loop \
  --manifest /app/knowledge/source-manifest.yml \
  --db /app/.data/knowledge.db \
  --downloads /app/.data/source-downloads
```

To use embeddings, provide the variables transiently from a shell or a Git-ignored env file, then
add `--embed`. Never place the key in Compose YAML, source manifests, documentation examples, or
Git history. Query-time remote embedding and reranking are separately opt-in; see
[`docs/knowledge-retrieval.md`](knowledge-retrieval.md).

The host `.data/knowledge.db` and `.data/source-downloads/` remain local. The tracked
`knowledge/catalog.snapshot.json` contains metadata, hashes, and health only. This protects source
licensing, user-derived material, and the ability to remove a downloaded copy without rewriting a
repository’s history.

## HTTP protection

`/healthz` is intentionally available for local health checks. The other HTTP endpoints use the
configured bearer token when `HELPME_CONSOLE_TOKEN` is set. Bind the service to loopback for local
use. If it is ever shared, put it behind HTTPS and a real identity/access layer; a static bearer
token is a minimum development gate, not a production account system.

Important endpoints:

- `/` — conversation-first browser surface.
- `/healthz` — health and audit-chain validity.
- `/api/sessions` and `/api/sessions/{id}/message` — natural-language session flow.
- `/api/expert/capabilities` — machine/skill/knowledge health metadata.
- `/api/knowledge/sources` — source provenance metadata.
- `/graphql` — read-only knowledge and retrieval projection.

## Dedicated VPS (optional)

Use a dedicated host, dedicated persistent volume, and a deployment-user-owned env file. Do not
point this service at unrelated business data. Preflight:

```bash
umask 077
mkdir -p /srv/helpme-green
touch /srv/helpme-green/.env
chmod 600 /srv/helpme-green/.env
```

The env file must contain a stable `HELPME_MASTER_KEY` and a strong `HELPME_CONSOLE_TOKEN`, plus the
model endpoint configuration. Keep it outside Git and do not print it in CI logs. Put the app behind
an HTTPS reverse proxy before sharing it.

The prepared deployment helper expects:

```bash
export HELPME_VPS_HOST=dedicated-host.example
export HELPME_VPS_USER=deploy
export HELPME_VPS_APP_DIR=/srv/helpme-green
export HELPME_VPS_ENV_FILE=/srv/helpme-green/.env
bash deploy/vps/deploy.sh
```

The helper builds the reviewed image, transfers the image, starts the container with the
pre-provisioned environment, and checks `/healthz`. It does not publish raw knowledge downloads or
the host database. Remote deployment is not considered complete until the actual target, TLS,
backup, restore, access, and source-licence controls have been tested.
