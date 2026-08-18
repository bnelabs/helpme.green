# Deployment and runtime boundaries

helpme.green is designed local-first. The supported short-term deployment is Docker Compose on the
operator’s machine, with an optional dedicated VPS deployment kept separate from business systems.
The application must not receive Konverta operational credentials or user data unless that boundary
has been deliberately designed and reviewed.

## Local Docker

Docker Compose exposes the web app only on `127.0.0.1:8080`. The container persists sessions, audit
history, the runtime knowledge database, and raw source downloads in the named `helpme_data` volume.
No particular local download is mounted into the conversation runtime; registered sources are used
through the normal knowledge pipeline.

Create the required encryption key in the current shell and start the app:

```bash
export HELPME_MASTER_KEY="$(python3 -c 'import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())')"
export HELPME_AI_ENABLED=1
export HELPME_MODEL='localai:auto'
export HELPME_LOCALAI_BASE_URL='http://127.0.0.1:8090/v1'  # replace with your model endpoint
docker compose up -d --build
curl http://127.0.0.1:8080/healthz
```

To enable image-assisted notebook comparisons through OpenRouter, configure the provider and a
vision-enabled model profile in the deployment environment. The selected original photos, selected
library example images, and all saved page details are then included in the comparison request; raw
image bytes are not written to the server session ledger or knowledge base:

```bash
export HELPME_MODEL='openrouter:dots-studio/dots-3-note-preview:free'
export OPENROUTER_API_KEY='set-in-your-shell-or-secret-manager'
export HELPME_MODEL_PROFILES='{"openrouter:dots-studio/dots-3-note-preview:free":{"vision":true,"include_reasoning":false,"max_tokens":8192,"timeout_seconds":180,"context_window":512000}}'
export HELPME_MAX_VISION_IMAGE_BYTES=16777216
export HELPME_MAX_VISION_REQUEST_BYTES=67108864
```

Do not paste provider keys into the browser access-token field; that field is only for
`HELPME_ACCESS_TOKEN`. With `HELPME_MASTER_KEY` configured, provider keys may instead be entered in
the app Settings surface and are stored encrypted in `.data`. Free model variants can be rate-limited
or unavailable; keep a tested fallback profile if the workflow needs continuity.

`localai:auto` asks the configured OpenAI-compatible local endpoint for its model list and selects
the model only when exactly one is advertised. If the endpoint serves multiple models, set
`HELPME_MODEL='localai:<model-id>'`. Keep model-specific sampling, context, reasoning, and timeout
settings in `HELPME_MODEL_PROFILES`; do not bake a model name into Compose or application code.

## Use a cloned, bootstrapped digest

The default Compose file keeps the runtime database in the named `helpme_data` volume. When a clone
has installed a reviewed artifact into `.data/knowledge.db`, use the host-data override so Docker
searches that exact database:

```bash
python3 scripts/bootstrap_knowledge.py
export HELPME_DATA_HOST_PATH="$PWD/.data"
docker compose -f docker-compose.yml -f docker-compose.host-data.yml up -d --build
```

The bootstrapper refuses the repository's current `pending-redistribution-review` manifest. That
is expected until a scrubbed, explicitly redistributable release asset has been published. The
override is also useful for a controlled private artifact supplied with explicit checksums. See
[`knowledge-artifact.md`](knowledge-artifact.md) for the publication and checksum contract.

`HELPME_MASTER_KEY` protects encrypted local BYOK storage. It is not a browser login token.
`HELPME_ACCESS_TOKEN` is optional. Leave it unset for a local no-token browser; set it only when a
token gate is wanted:

```bash
export HELPME_ACCESS_TOKEN='local-development-only-token'
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
add `--embed`. OpenRouter and loopback LocalAI embedding endpoints are supported. Query-time use is
automatic only when the corresponding feature is enabled: the Compose defaults deliberately set
`HELPME_EMBEDDING_QUERY_ENABLED=0` and `HELPME_RERANK_ENABLED=0`, so opt in explicitly when the
endpoint, model, and provider-disclosure decision are ready. Never place the key in Compose YAML,
source manifests, documentation examples, or Git history. See
[`docs/knowledge-retrieval.md`](knowledge-retrieval.md).

The host `.data/knowledge.db` and `.data/source-downloads/` remain local by default. The tracked
`knowledge/catalog.snapshot.json` and `knowledge/artifact-manifest.json` contain metadata, hashes,
coverage, and publication status only. A reviewed release artifact may be installed explicitly;
the current full digest is not silently copied into Git history or a public release.

## HTTP protection

`/healthz` is intentionally available for local health checks. The other HTTP endpoints use the
configured bearer token when `HELPME_ACCESS_TOKEN` is set. Bind the service to loopback for local
use. If it is ever shared, put it behind HTTPS and a real identity/access layer; a static bearer
token is a minimum development gate, not a production account system.

Important endpoints:

- `/` — conversation-first browser surface.
- `/healthz` — health and audit-chain validity.
- `/api/sessions` and `/api/sessions/{id}/message` — natural-language session flow.
- `/api/sessions/{id}/message/stream` — SSE progress and reply-delta flow used by the browser.
- `/api/runtime/model` — configured provider/model identity without secrets.
- `/api/settings` — validated local provider/model and app settings; provider keys are write-only.
- `/api/expert/capabilities` — machine/skill/knowledge health metadata.
- `/api/knowledge/sources` — source provenance metadata.
- `/graphql` — read-only knowledge and retrieval projection.
- `/api/kb/*` — disabled-by-default, operator-authenticated knowledge-base management routes; see
  [`kb-operator-runbook.md`](kb-operator-runbook.md).

## Public onboarding site

The static newcomer guide is published separately from the local-first runtime at
<https://bnelabs.github.io/helpme.green/>. The checked-in
[Pages workflow](../.github/workflows/pages.yml) serves only `website/` on pushes to `main` or an
explicit workflow dispatch. It contains onboarding copy, screenshots, and installation guidance;
it does not expose `.data`, runtime databases, provider keys, raw source downloads, or model files.

The release workflow is checked in and has produced the draft `v0.1.0-rc.6` candidate from tagged
commit `955d8ed9779c36d660fe86f5ca3241313a426b7f`. It passed the six native bundle smoke checks and
the multi-platform container rehearsal. `main` now contains post-tag onboarding and documentation
updates, so changes after the tag are not represented by the existing binary; create a new candidate
rather than moving the immutable tag. The candidate remains a draft pre-release: macOS and Windows bundles
are unsigned until the stable signing/notarization secrets are configured. Use the [GitHub Releases
page](https://github.com/bnelabs/helpme.green/releases) for the current candidate and checksums
rather than copying binary assets into the repository. Treat the candidate as controlled-test
software: automated checks are evidence of the build path, not a promise of stability; occasional
breakage, rough edges, and behavior changes are still possible.

## Dedicated VPS (optional)

Use a dedicated host, dedicated persistent volume, and a deployment-user-owned env file. Do not
point this service at unrelated business data. Preflight:

```bash
umask 077
mkdir -p /srv/helpme-green
touch /srv/helpme-green/.env
chmod 600 /srv/helpme-green/.env
```

The env file must contain a stable `HELPME_MASTER_KEY` and a strong `HELPME_ACCESS_TOKEN`, plus the
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
