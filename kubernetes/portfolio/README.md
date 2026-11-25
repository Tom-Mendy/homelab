# Portfolio

This chart deploys the static Astro portfolio from `Tom-Mendy/Portfolio`.
Portfolio now runs on Talos. Its retained Ubuntu release is suspended for
rollback. See the [migration record](../../docs/talos-portfolio-migration.md)
for the active route and recovery procedure. The descriptions below retain
the original Ubuntu chart and automation behavior for reference.

Forgejo Actions builds and publishes the image at
`harbor.home.tom-mendy.com/portfolio/portfolio`. The deployment pins the
published OCI index digest in `values.yaml`.

Image automation remains suspended during migration. The original automation
scans the private Harbor repository every minute. Its image policy follows
only the mutable `latest` tag and reflects its digest. When that digest changes,
Flux commits the new value to `main`; the normal Git reconciliation then rolls
out the new image. The tag stays readable, while the digest fixes the exact
artifact recorded in Git.

Run the setup wizard once before enabling the automation:

```sh
./scripts/setup-portfolio-image-automation.sh
```

The wizard creates no credentials in this repository. It walks through a
pull-only Harbor robot, the matching Infisical secret, a dedicated writable
Forgejo deploy key, and the two optional Flux image controllers.

## Kubernetes

Talos Flux reconciles the isolated manifests in `talos/gitops/apps/portfolio`.
One nginx replica serves port 8080 behind a ClusterIP service on port 80. The
Pod has no persistent data. The original Ubuntu Helm chart is retained with
its Deployment stopped and HelmRelease suspended for rollback.

Talos Traefik serves `tom-mendy.com` using ingress class `talos-traefik`.
Local HTTPS uses the imported application certificate; public HTTPS is
terminated by Pangolin with its own certificate resolver. The public A record points
to the Pangolin VPS at `92.222.90.223`. Blocky intentionally has no custom DNS
entry for this public hostname.

## Pangolin route

Pangolin is managed outside this repository. Its public HTTP resource must use:

```text
Domain: tom-mendy.com
Site: K8s
Target: 10.0.0.70:80
Method: HTTP
```

Set the Host header to `tom-mendy.com` so the Talos ingress selects Portfolio.
The former Ubuntu target `portfolio.portfolio.svc.cluster.local:80` is used
only for rollback after the original Deployment is ready.

## Verification

```sh
flux get image repository portfolio --namespace flux-system
flux get image policy portfolio --namespace flux-system
flux get image update portfolio --namespace flux-system
flux get helmrelease portfolio --namespace flux-system
kubectl -n portfolio rollout status deployment/portfolio
kubectl -n portfolio get deployment portfolio \
  -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
kubectl -n portfolio get endpointslice -l kubernetes.io/service-name=portfolio
curl -fsS https://tom-mendy.com/
```

The image reported by the Deployment must equal the `latestRef` name, tag, and
digest reported by the image policy. To pause automatic commits during an
incident:

```sh
flux suspend image update portfolio --namespace flux-system
```

Resume image automation only after the migration freeze is explicitly ended.
Keep the Ubuntu Portfolio HelmRelease suspended after migration.
Rollback by reverting the image update commit. Flux will restore the previous
digest.
