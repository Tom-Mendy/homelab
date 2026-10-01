#!/usr/bin/env python3
"""Keep the owner-operated Hermes workspace running and verify cluster access."""

import json
import os
import subprocess
import time
import urllib.request


WORKSPACE = "nainjoueur/hermes"


def api(path):
    request = urllib.request.Request(
        os.environ["CODER_URL"].rstrip("/") + "/api/v2/" + path,
        headers={"Coder-Session-Token": os.environ["CODER_SESSION_TOKEN"]},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def coder(*args):
    subprocess.run(["coder", *args], input="yes\n", text=True, check=True, timeout=900)


def main():
    workspace = api("users/nainjoueur/workspace/hermes")
    if workspace["template_name"] != "hermes-personal":
        raise RuntimeError("The Hermes workspace uses an unexpected template")
    coder("templates", "edit", "hermes-personal", "--private=true",
          "--default-ttl=0", "--yes")
    coder("schedule", "stop", WORKSPACE, "manual")
    coder("update", WORKSPACE)
    coder("start", WORKSPACE, "--yes")

    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        workspace = api("users/nainjoueur/workspace/hermes")
        status = workspace["latest_build"]["status"]
        if status in ("failed", "canceled", "deleted"):
            raise RuntimeError(f"Hermes workspace build is {status}")
        agents = [agent for resource in workspace["latest_build"].get("resources", [])
                  for agent in resource.get("agents", [])]
        if status == "running" and agents and all(
            agent.get("status") == "connected"
            and agent.get("lifecycle_state") == "ready" for agent in agents
        ):
            break
        time.sleep(5)
    else:
        raise TimeoutError("Hermes did not become ready within ten minutes")

    if workspace.get("ttl_ms") not in (None, 0):
        raise RuntimeError("Hermes still has an automatic stop schedule")
    if workspace["latest_build"].get("deadline"):
        raise RuntimeError("Hermes still has a scheduled shutdown deadline")

    # This runs inside Hermes, using its projected token, never CI credentials.
    command = r'''bash -lc '
set -euo pipefail
test "$KUBECONFIG" = /opt/data/.kube/hermes.config
kubectl auth whoami
test "$(kubectl auth can-i "*" "*" --all-namespaces)" = yes
kubectl get nodes -o wide
kubectl -n coder-workspaces get pods,pvc -l app.kubernetes.io/name=hermes-workspace -o wide
name="hermes-access-check-$(date +%s)"
trap "kubectl -n coder-workspaces delete configmap $name --ignore-not-found" EXIT
kubectl -n coder-workspaces create configmap "$name" --from-literal=verified=true
test "$(kubectl -n coder-workspaces get configmap "$name" -o jsonpath={.data.verified})" = true
helm version --short
flux --version
jq --version
gateway_ready=false
for attempt in $(seq 1 30); do
  if hermes gateway status | grep -F "Gateway is running"; then
    gateway_ready=true
    break
  fi
  sleep 2
done
$gateway_ready
hermes gateway status
' '''
    coder("ssh", "--disable-autostart", WORKSPACE, "--", command)
    print("Hermes is ready, has no shutdown deadline, and passed cluster read/write checks.")


if __name__ == "__main__":
    main()
