# Fix Forgejo LFS Push

## Problem

`git push` to Forgejo failed before uploading refs because Git LFS attempted
the locking verification API:

```text
Remote "origin" does not support the Git LFS locking API.
Fatal error: Server error ...
/tom-mendy/homelab.git/info/lfs/locks/verify ... HTTP 503
error: failed to push some refs to 'forgejo:tom-mendy/homelab.git'
```

The global setting already had `lfs.locksverify=false`, but repository-local
settings still forced lock verification for Forgejo endpoints.

## Reasoning

Inspect the active LFS lock settings:

```sh
git config --show-origin --get-regexp '^(remote\.|lfs\.|url\.|filter\.lfs)'
git lfs logs last
git status --short --branch
```

Relevant output:

```text
file:/home/tmendy/.gitconfig    lfs.locksverify false
file:.git/config lfs.https://forgejo.home.../info/lfs.locksverify true
file:.git/config lfs.https://forgejo/.../info/lfs.locksverify true
file:.git/config lfs.https://forgejo.tom-mendy.com.../info/lfs.locksverify false
```

The failing LFS endpoint was:

```text
Endpoint=https://forgejo/tom-mendy/homelab.git/info/lfs
```

So the exact matching local config key still had `locksverify=true`.

## Change

Set all Forgejo LFS endpoints in this clone to disable lock verification:

```text
lfs.https://forgejo/tom-mendy/homelab.git/info/lfs.locksverify=false
lfs.https://forgejo.home.../homelab.git/info/lfs.locksverify=false
lfs.https://forgejo.tom-mendy.com.../info/lfs.locksverify=false
```

Validate:

```sh
git config --show-origin --get-regexp 'lfs.*locksverify'
git lfs env
git push origin main
```

Observed push result:

```text
To forgejo:tom-mendy/homelab.git
   e9cf042..ce9232e  main -> main
```

## Kubernetes Checks

Forgejo itself was checked because the original error included HTTP 503:

```sh
kubectl get pods,svc,ingress -n forgejo -o wide
kubectl rollout status deploy/forgejo -n forgejo
kubectl logs -n forgejo deploy/forgejo --tail=120
```

Observed output:

```text
pod/forgejo-f8df4888c-hndgv   1/1   Running   0   9d
service/forgejo   ClusterIP   10.233.41.167   <none>   3000/TCP,22/TCP
ingress.networking.k8s.io/forgejo-ingress   traefik   forgejo.home.tom-mendy.com
deployment "forgejo" successfully rolled out
```

Recent logs showed successful SSH Git operations and the successful push path:

```text
completed GET ... verb=git-receive-pack ... 200 OK
completed GET ... verb=git-lfs-authenticate&verb=upload ... 200 OK
completed POST ... hook/pre-receive/tom-mendy/homelab ... 200 OK
completed POST ... hook/post-receive/tom-mendy/homelab ... 200 OK
```

## Outcome

`git push origin main` works again for this clone. Forgejo pod and rollout are
healthy. The root issue was repository-local Git LFS lock verification still
enabled for the `https://forgejo/.../info/lfs` endpoint.
