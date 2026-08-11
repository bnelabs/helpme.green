# Phase A VPS deployment

The console is packaged as a single container. Deployment is intentionally separate from the
Konverta operational systems: use a dedicated VPS, dedicated data volume, and a pre-provisioned
secret environment file. Do not point this application at Konverta data or credentials.

## Local Docker deployment

The reviewed checkout can run locally with Docker Compose. The published port is bound to
loopback only on 127.0.0.1:8080; the API remains bearer-token protected.

Set a local-only development token and generate a Fernet key in the shell that starts Compose:

```bash
export HELPME_CONSOLE_TOKEN=local-development-only-token
export HELPME_MASTER_KEY="$(.venv/bin/python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
docker compose up -d --build
curl http://127.0.0.1:8080/healthz
```

Open http://localhost:8080 in a browser, enter the local development token, and click Connect
to use the Pro Console. The page sends the token only as a bearer header to the protected API.

Use the bearer token for API requests. The Compose volume preserves sessions, snapshots, and
audit history across container restarts:

```bash
curl -H 'Authorization: Bearer local-development-only-token' \
  http://127.0.0.1:8080/healthz
docker compose ps
docker compose logs --no-color
```

For a long-lived local installation, keep the same HELPME_MASTER_KEY in a Git-ignored local
environment file with restrictive permissions. Never commit it or reuse it for a VPS.

## Preflight

On the VPS, install Docker and provision an env file readable only by the deployment user:

```bash
umask 077
mkdir -p /srv/helpme-green
touch /srv/helpme-green/.env
chmod 600 /srv/helpme-green/.env
```

The file must contain `HELPME_CONSOLE_TOKEN` and `HELPME_MASTER_KEY`. Generate the Fernet master
key with the runtime, and keep it outside Git and shell history:

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```

Put the console behind an HTTPS reverse proxy before sharing the URL. The bearer token is a
minimum Phase A gate, not a complete account system.

## Deploy

From the exact reviewed checkout, set only non-secret deployment metadata and run:

```bash
export HELPME_VPS_HOST=dedicated-host.example
export HELPME_VPS_USER=deploy
export HELPME_VPS_APP_DIR=/srv/helpme-green
export HELPME_VPS_ENV_FILE=/srv/helpme-green/.env
bash deploy/vps/deploy.sh
```

The script builds the current commit, transfers only the image, starts the container with the
pre-provisioned env file and persistent data volume, then requires `/healthz` to pass. It never
prints secret values and never sends the source tree or knowledge data outside the image transfer.
