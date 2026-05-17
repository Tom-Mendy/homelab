# Add Forgejo Actions Runner for Homelab

## Problem

The `homelab` repository was being moved from GitHub-primary to
Forgejo-primary. Pushing to Forgejo failed because the Forgejo repository was a
read-only pull mirror:

```text
Forgejo: Mirror Repository tom-mendy/homelab is read-only
fatal: Could not read from remote repository.
```

The existing CI workflow lived under `.github/workflows/` and used GitHub
Actions Runner Controller. The target state was Forgejo Actions CI with GitHub
left as a mirror.

## Reasoning path

Check the Forgejo remote and local branch tracking:

```sh
git remote -v
git branch -vv
```

Observed remotes after switching `origin`:

```text
github  git@github.com:Tom-Mendy/homelab.git (fetch)
github  git@github.com:Tom-Mendy/homelab.git (push)
origin  ssh://git@forgejo.home.tom-mendy.com/tom-mendy/homelab.git (fetch)
origin  ssh://git@forgejo.home.tom-mendy.com/tom-mendy/homelab.git (push)
```

Verify the Forgejo repository state from the Forgejo SQLite database:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo exec deploy/forgejo -- \
  sqlite3 /data/gitea/gitea.db \
  "select r.id,u.name,r.name,r.is_mirror
   from repository r join user u on u.id=r.owner_id where r.id=3;"
```

Observed:

```text
3|Tom-Mendy|homelab|1
```

Forgejo CLI exposed runner registration commands:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo exec deploy/forgejo -- \
  su git -c 'forgejo forgejo-cli actions register --help'
```

Relevant output:

```text
--secret string            the 40 character hexadecimal runner secret
--scope string, -s string  {owner}[/{repo}] - leave empty for a global runner
--name string              name of the runner (default runner)
```

## Commands and results

Back up the Forgejo database and convert the repository from mirror to writable:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo exec deploy/forgejo -- \
  sqlite3 /data/gitea/gitea.db \
  ".backup '/data/gitea/gitea.db.pre-forgejo-ci-20260517'"

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo exec deploy/forgejo -- \
  sqlite3 /data/gitea/gitea.db \
  "update repository set is_mirror=0 where id=3 and lower_name='homelab';
   delete from mirror where repo_id=3;"
```

Verify:

```text
3|Tom-Mendy|homelab|0
```

Register a repo-scoped Forgejo runner and store the UUID/token in a Kubernetes
Secret. The token was not stored in Git:

```sh
secret="$(openssl rand -hex 20)"
uuid="$(kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo exec deploy/forgejo -- \
  su git -c "forgejo forgejo-cli actions register \
    --name forgejo-runner-homelab \
    --scope Tom-Mendy/homelab \
    --secret $secret")"

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  create namespace forgejo-runner --dry-run=client -o yaml | \
  kubectl --kubeconfig /home/tmendy/.kube/config-homelab apply -f -

kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo-runner create secret generic forgejo-runner-homelab \
  --from-literal=uuid="$uuid" \
  --from-literal=token="$secret" \
  --dry-run=client -o yaml | \
  kubectl --kubeconfig /home/tmendy/.kube/config-homelab apply -f -
```

Observed:

```text
namespace/forgejo-runner created
secret/forgejo-runner-homelab created
uuid=39303865-3866-6535-6230-656162393836
secret_sha256=REMOVED_API_KEY
```

Initial push without the explicit key failed because the escalated shell did
not have access to the SSH agent:

```text
git@forgejo.home.tom-mendy.com: Permission denied (publickey).
fatal: Could not read from remote repository.
```

Retry with the Forgejo key:

```sh
GIT_SSH_COMMAND='ssh -i /home/tmendy/.ssh/forgejo_key -o IdentitiesOnly=yes' \
  git push -u origin main
```

Result:

```text
To ssh://forgejo.home.tom-mendy.com/tom-mendy/homelab.git
   4157193..76548c9  main -> main
branch 'main' set up to track 'origin/main'.
```

Argo CD did not process the new Application at first because the application
controller pod was stuck terminating on `node3`, which was NotReady:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab get nodes -o wide
```

Observed:

```text
NAME    STATUS     ROLES           INTERNAL-IP
node1   Ready      control-plane   192.168.1.11
node2   Ready      <none>          192.168.1.12
node3   NotReady   <none>          192.168.1.13
```

The stuck controller pod:

```text
argocd-application-controller-0   1/1   Terminating   node3
```

Force-delete the stale pod so the StatefulSet could recreate it:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n argocd delete pod argocd-application-controller-0 \
  --grace-period=0 --force
```

Result:

```text
pod "argocd-application-controller-0" force deleted
```

The replacement scheduled on `node2`:

```text
argocd-application-controller-0   1/1   Running   node2
```

After the first runner deploy, the pod entered `CrashLoopBackOff`:

```text
pod/forgejo-runner-homelab-7b99b77bcf-kdwl5   0/2   CrashLoopBackOff
```

Check previous container logs:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  -n forgejo-runner logs deploy/forgejo-runner-homelab \
  -c docker --previous --tail=120
```

The Docker sidecar showed:

```text
/usr/local/bin/docker-entrypoint.sh: exec: line 61: dockerd-rootless.sh: not found
```

The runner container then failed because Docker was not running:

```text
Error: cannot ping the docker daemon. is it running? Cannot connect to the
Docker daemon at tcp://127.0.0.1:2375. Is the docker daemon running?
```

The initial attempted fix removed the explicit `dockerd-rootless.sh` argument,
but the next rootless Docker crash showed seccomp blocking rootlesskit:

```text
[rootlesskit:parent] error: failed to start the child:
fork/exec /proc/self/exe: operation not permitted
```

After re-reading the official Forgejo Docker-in-Docker documentation, the
rootless DIND approach was replaced with the documented pattern:

- use privileged `docker:dind`
- start `dockerd -H tcp://0.0.0.0:2375 --tls=false`
- set runner `container.docker_host` to the DIND daemon
- set runner `runner.envs.DOCKER_HOST` for job containers
- add `container.options` with a host-gateway mapping for job containers

The corrected chart rendered and passed server-side dry-run:

```sh
helm template test kubernetes/forgejo-runner | \
  kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  apply --dry-run=server -f -
```

Result:

```text
namespace/forgejo-runner configured (server dry run)
configmap/forgejo-runner-config configured (server dry run)
deployment.apps/forgejo-runner-homelab configured (server dry run)
```

## Final outcome

The repository now contains:

- Forgejo Actions workflow under `.forgejo/workflows/storage-policy.yml`
- Forgejo runner chart under `kubernetes/forgejo-runner/`
- Argo CD app `forgejo-runner-homelab`
- Forgejo Actions config in the Forgejo deployment
- removal of the homelab GitHub ARC runner app and values file

The live Forgejo repository is writable, and the runner token is stored in the
`forgejo-runner` namespace as `forgejo-runner-homelab`.
