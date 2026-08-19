"""Guard the isolated MicroK8s deployment contract."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
K8S_ROOT = ROOT / "deploy" / "k8s"
DEPLOY_WORKFLOW = ROOT / ".github" / "workflows" / "deploy-hetzner.yml"


def _resources() -> list[dict[str, object]]:
    resources: list[dict[str, object]] = []
    for path in sorted(K8S_ROOT.glob("*.yaml")):
        if path.name == "kustomization.yaml":
            continue
        loaded = list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        resources.extend(item for item in loaded if isinstance(item, dict))
    return resources


def _resource(kind: str, name: str) -> dict[str, object]:
    for item in _resources():
        metadata = item.get("metadata", {})
        if item.get("kind") == kind and isinstance(metadata, dict) and metadata.get("name") == name:
            return item
    raise AssertionError(f"Missing {kind}/{name}")


def test_deployment_isolated_from_public_site_and_uses_persistent_health_checked_runtime() -> None:
    deployment = _resource("Deployment", "helpme-green")
    spec = deployment["spec"]
    assert isinstance(spec, dict)
    assert spec["replicas"] == 1
    assert spec["strategy"] == {"type": "Recreate"}
    pod_spec = spec["template"]["spec"]
    container = pod_spec["containers"][0]
    assert container["image"] == "localhost:32000/helpme-green:latest"
    assert container["envFrom"] == [
        {"configMapRef": {"name": "helpme-green-runtime"}},
        {"secretRef": {"name": "helpme-green-runtime"}},
    ]
    assert container["startupProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert container["readinessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert container["livenessProbe"]["httpGet"] == {"path": "/healthz", "port": "http"}
    assert deployment["metadata"]["namespace"] == "helpme-green"


def test_runtime_configuration_is_openrouter_multimodal_without_embedded_secret() -> None:
    config = _resource("ConfigMap", "helpme-green-runtime")
    data = config["data"]
    assert isinstance(data, dict)
    assert data["HELPME_MODEL"] == "openrouter:dots-studio/dots-3-note-preview:free"
    profile = json.loads(data["HELPME_MODEL_PROFILES"])
    assert profile["openrouter:dots-studio/dots-3-note-preview:free"]["vision"] is True
    assert "OPENROUTER_API_KEY" not in data
    assert "HELPME_MASTER_KEY" not in data


def test_hostname_and_storage_are_scoped_to_helpme_green() -> None:
    ingress = _resource("Ingress", "helpme-green")
    ingress_spec = ingress["spec"]
    assert ingress_spec["rules"][0]["host"] == "green.konverta.eu"
    assert (
        ingress_spec["rules"][0]["http"]["paths"][0]["backend"]["service"]["name"] == "helpme-green"
    )

    pvc = _resource("PersistentVolumeClaim", "helpme-green-data")
    assert pvc["spec"]["storageClassName"] == "microk8s-hostpath"
    assert pvc["spec"]["resources"]["requests"]["storage"] == "10Gi"

    for item in _resources():
        metadata = item.get("metadata", {})
        if isinstance(metadata, dict) and item.get("kind") != "Namespace":
            assert metadata.get("namespace") == "helpme-green"


def test_hetzner_workflow_deploys_only_successful_main_ci_runs() -> None:
    workflow = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_run:" in workflow
    assert 'workflows: ["CI"]' in workflow
    assert "types: [completed]" in workflow
    assert "github.event.workflow_run.event == 'push'" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow
    assert (
        "github.event.workflow_run.head_branch == github.event.repository.default_branch"
        in workflow
    )
    assert "--platform linux/amd64" in workflow
    assert "microk8s ctr images import" in workflow
    assert "microk8s kubectl apply -k" in workflow
    assert "HETZNER_SSH_PRIVATE_KEY" in workflow
    assert "HETZNER_SSH_KNOWN_HOSTS" in workflow
    assert "OPENROUTER_API_KEY" not in workflow
    assert "website/" not in workflow
