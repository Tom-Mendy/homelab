# Forgejo Runner for Homelab

This chart deploys one Forgejo Actions runner for
`Tom-Mendy/homelab`.

The runner uses:

- `data.forgejo.org/forgejo/runner:12`
- `docker:dind`
- `runs-on: ubuntu-latest`
- runner label `ubuntu-latest:docker://ghcr.io/catthehacker/ubuntu:act-latest`

The Docker sidecar follows the Forgejo Docker-in-Docker guidance: a separate
privileged `docker:dind` daemon is exposed only inside the pod, and the runner
sets both `runner.envs.DOCKER_HOST` and `container.docker_host` to that daemon.
Job containers receive `DOCKER_HOST=tcp://dind.docker.internal:2375`, with
`container.options` mapping that name to Docker's host gateway.

The runner process runs `forgejo-runner one-job --wait` in a container-local
loop. Each completed job gets a fresh poller without restarting the pod; failed
polls retry after five seconds instead of entering a tight loop.

## Secret

The runner registration secret is not stored in Git. Create it from the UUID
and token returned by Forgejo:

```sh
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n forgejo-runner create secret generic forgejo-runner-homelab \
  --from-literal=uuid='<RUNNER_UUID>' \
  --from-literal=token='<RUNNER_TOKEN>'
```

## Registration

Offline registration is done from the Forgejo pod:

```sh
secret="$(openssl rand -hex 20)"
kubectl --kubeconfig "$HOME/.kube/config-homelab" \
  -n forgejo exec deploy/forgejo -- \
  su git -c "forgejo forgejo-cli actions register \
    --name forgejo-runner-homelab \
    --scope Tom-Mendy/homelab \
    --secret $secret"
```

The command prints the UUID. Store the UUID and the same generated secret in the
`forgejo-runner-homelab` Kubernetes Secret.
