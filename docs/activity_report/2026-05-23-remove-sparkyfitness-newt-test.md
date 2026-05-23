# Remove sparkyfitness and newt-test from cluster

## Problem

Remove the `sparkyfitness` and `newt-test` workloads from the homelab
Kubernetes cluster.

`sparkyfitness` was especially important to remove because it still used
`local-path` PVCs, which violates the repository storage policy. `newt-test`
was requested for removal, but no live namespace was found.

## Reasoning path

First, search the repository for managed manifests or documentation mentioning
the requested names:

```sh
rg -n "sparkyfitness|newt-test|newt" .
```

Result:

```text
kubernetes/argocd/apps/newt.yaml:4:  name: newt
kubernetes/newt/newt-values.yaml:7:newtInstances:
kubernetes/newt/newt-creds.yaml:4:  name: newt-creds
docs/activity_report/2026-05-14-ollama-pvc-migration.md:317:sparkyfitness/sparkyfitness-backup-pvc
docs/activity_report/2026-05-14-ollama-pvc-migration.md:318:sparkyfitness/sparkyfitness-db-pvc
docs/activity_report/2026-05-14-ollama-pvc-migration.md:319:sparkyfitness/sparkyfitness-uploads-pvc
```

This showed `newt` is GitOps-managed, but `newt-test` is not present in the
repo. `sparkyfitness` appeared only in prior reports, not active manifests.

The first live cluster query failed because the default kubeconfig was empty
and `kubectl` tried `localhost:8080`:

```sh
kubectl get ns
```

Result:

```text
The connection to the server localhost:8080 was refused -
did you specify the right host or port?
```

The repository activity reports showed the correct kubeconfig path:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab get ns
```

Important result:

```text
NAME            STATUS   AGE
sparkyfitness   Active   66d
```

`newt-test` was not listed.

Inspect `sparkyfitness` resources:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  get all,pvc,ingress -n sparkyfitness
```

Important result:

```text
pod/sparkyfitness-db-78976bb9bc-2ffz8         0/1   Pending       0   4d23h
pod/sparkyfitness-db-78976bb9bc-9c54t         1/1   Terminating   0   6d16h
pod/sparkyfitness-frontend-7dbdfcc47c-mwrfz   1/1   Running       5   12d
pod/sparkyfitness-server-7bdfccb769-5w4mk     1/1   Terminating   0   6d16h
pod/sparkyfitness-server-7bdfccb769-brcrr     0/1   Pending       0   4d23h

persistentvolumeclaim/sparkyfitness-backup-pvc    Bound   ...   local-path
persistentvolumeclaim/sparkyfitness-db-pvc        Bound   ...   local-path
persistentvolumeclaim/sparkyfitness-uploads-pvc   Bound   ...   local-path
```

Inspect `newt-test`:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  get all,pvc,ingress -n newt-test
```

Result:

```text
No resources found in newt-test namespace.
```

Delete the requested namespaces:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  delete namespace sparkyfitness newt-test --ignore-not-found
```

Result:

```text
namespace "sparkyfitness" deleted
```

The command waited because `sparkyfitness` remained in `Terminating`. Inspecting
leftovers showed old terminating pods and remaining PVCs, services,
deployments, and ingress.

Force-delete the old terminating pods and delete remaining namespaced objects:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab -n sparkyfitness \
  delete pod sparkyfitness-db-78976bb9bc-9c54t \
  sparkyfitness-server-7bdfccb769-5w4mk \
  --grace-period=0 --force

kubectl --kubeconfig /home/tmendy/.kube/config-homelab -n sparkyfitness \
  delete all,pvc,ingress --all --ignore-not-found
```

Result:

```text
pod "sparkyfitness-db-78976bb9bc-9c54t" force deleted
pod "sparkyfitness-server-7bdfccb769-5w4mk" force deleted
service "sparkyfitness" deleted
service "sparkyfitness-db" deleted
service "sparkyfitness-server" deleted
deployment.apps "sparkyfitness-db" deleted
deployment.apps "sparkyfitness-frontend" deleted
deployment.apps "sparkyfitness-server" deleted
persistentvolumeclaim "sparkyfitness-backup-pvc" deleted
persistentvolumeclaim "sparkyfitness-db-pvc" deleted
persistentvolumeclaim "sparkyfitness-uploads-pvc" deleted
ingress.networking.k8s.io "sparkyfitness-ingress" deleted
```

After namespace deletion, three `sparkyfitness` `local-path` PV objects remained
in `Released` state:

```text
PV pvc-34c23c6c-360e-4453-8b4a-f8bbde89f266:
  Released, sparkyfitness/sparkyfitness-backup-pvc, local-path
PV pvc-6b24e090-af6c-48b0-ad62-25a359d2db14:
  Released, sparkyfitness/sparkyfitness-uploads-pvc, local-path
PV pvc-a61869b5-257a-46ab-ad18-331fcaa58627:
  Released, sparkyfitness/sparkyfitness-db-pvc, local-path
```

Delete those PV objects:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab delete pv \
  pvc-34c23c6c-360e-4453-8b4a-f8bbde89f266 \
  pvc-6b24e090-af6c-48b0-ad62-25a359d2db14 \
  pvc-a61869b5-257a-46ab-ad18-331fcaa58627
```

Result:

```text
persistentvolume "pvc-34c23c6c-360e-4453-8b4a-f8bbde89f266" deleted
persistentvolume "pvc-6b24e090-af6c-48b0-ad62-25a359d2db14" deleted
persistentvolume "pvc-a61869b5-257a-46ab-ad18-331fcaa58627" deleted
```

## Verification

Confirm both requested namespaces are absent:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab get ns sparkyfitness newt-test
```

Result:

```text
Error from server (NotFound): namespaces "sparkyfitness" not found
Error from server (NotFound): namespaces "newt-test" not found
```

Confirm no resources remain in `sparkyfitness`:

```sh
kubectl --kubeconfig /home/tmendy/.kube/config-homelab \
  get all,pvc,ingress -n sparkyfitness
```

Result:

```text
No resources found in sparkyfitness namespace.
```

Confirm no active manifest under `kubernetes/` uses `local-path`:

```sh
rg -n "local-path" kubernetes
```

Result: no matches.

Run the repository storage policy check:

```sh
./scripts/check-storage-policy.sh
```

Result:

```text
storage policy ok
```

## Final outcome

`sparkyfitness` was removed from the cluster. Its namespace, workloads,
services, ingress, PVCs, and leftover `local-path` PV objects were removed.

`newt-test` was already absent; no namespace or resources were found.

No repo manifests were changed for workloads because neither `sparkyfitness`
nor `newt-test` had active manifests in this repository.
