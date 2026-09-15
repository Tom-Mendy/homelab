# Portfolio

This chart deploys the static Astro portfolio from `Tom-Mendy/Portfolio`.
Forgejo Actions builds and publishes the image at
`harbor.home.tom-mendy.com/portfolio/portfolio`. The deployment pins the
published OCI index digest in `values.yaml`.

Flux scans the private Harbor repository every minute. Its image policy follows
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

Flux installs the chart in the `portfolio` namespace. It runs two nginx
replicas on port 8080 behind a ClusterIP service on port 80. The pods have no
persistent data and use a hostname spread constraint so the scheduler places
them on separate workers when possible.

Traefik serves the Ingress for `tom-mendy.com` and obtains the certificate with
the existing Cloudflare DNS-01 resolver. The public Cloudflare A record points
to the Pangolin VPS at `92.222.90.223`. Blocky intentionally has no custom DNS
entry for this public hostname.

## Pangolin route

Pangolin is managed outside this repository. Its public HTTP resource must use:

```text
Domain: tom-mendy.com
Site: K8s
Target: portfolio.portfolio.svc.cluster.local:80
Method: HTTP
```

Keep the target namespace spelled `portfolio`. A typo such as
`portfolio.porfolio.svc.cluster.local` returns HTTP 503 from Pangolin.

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

Resume with `flux resume image update portfolio --namespace flux-system`.
Rollback by reverting the image update commit. Flux will restore the previous
digest.
