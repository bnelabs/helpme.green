# MicroK8s deployment

This package deploys only the helpme.green application. It does not modify the public
`website/` artifact or the existing `konverta` namespace.

## Runtime secret

Create the `helpme-green-runtime` Secret in the `helpme-green` namespace through the
operator's secret-management procedure. It must contain only:

- `HELPME_MASTER_KEY`: a stable Fernet-compatible key for encrypted application storage.
- `OPENROUTER_API_KEY`: the provider key for the configured OpenRouter model.

Never commit this Secret or place provider keys in this directory. The deployment intentionally
does not set `HELPME_ACCESS_TOKEN`: Cloudflare Access is the browser identity boundary for the
public hostname.

## Automated apply

[`deploy-hetzner.yml`](../../.github/workflows/deploy-hetzner.yml) deploys the application after a
successful `CI` workflow run for a push to `main`. It builds a Linux amd64 image, transfers it over
SSH, imports it into the MicroK8s container runtime, applies this Kustomize package, and waits for
the `helpme-green` rollout to become ready. The workflow never changes `website/` and never creates
or updates the runtime Secret.

Configure these repository secrets before enabling the workflow:

- `HETZNER_HOST`
- `HETZNER_SSH_USER`
- `HETZNER_SSH_PRIVATE_KEY` — a dedicated deploy key, not a personal root key.
- `HETZNER_SSH_KNOWN_HOSTS` — the pinned SSH host-key line(s) for the server.

The SSH account must be able to run `microk8s ctr`, `microk8s kubectl`, `mktemp`, `tar`, and `sed`.
Keep the account scoped to this host and protect `main` with required CI checks before storing a
deployment key in GitHub Actions.

## Manual apply

Build and publish `localhost:32000/helpme-green:<commit>` to the MicroK8s registry, update the
`images.newTag` value in `kustomization.yaml`, create the runtime Secret, then apply:

```bash
microk8s kubectl apply -k deploy/k8s
microk8s kubectl -n helpme-green rollout status deployment/helpme-green
```

The existing Cloudflare tunnel wildcard and DNS record already cover `green.konverta.eu`.
The Ingress adds the hostname-specific Kubernetes route and asks the existing `letsencrypt-prod`
ClusterIssuer for the origin certificate.

This is deliberately a single-replica SQLite deployment using the MicroK8s hostpath storage
class. Before treating it as production-complete, test an off-host backup and restore of the
PVC data and record the rollback image tag.
