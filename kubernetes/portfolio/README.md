# Portfolio

This chart deploys the static Astro portfolio from `Tom-Mendy/Portfolio`.
Forgejo Actions builds and publishes the image at
`forgejo.tom-mendy.com/tom-mendy/portfolio`. The deployment pins the published
OCI index digest in `values.yaml`; update it when a new portfolio commit is
published.

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
flux get helmrelease portfolio --namespace flux-system
kubectl -n portfolio rollout status deployment/portfolio
kubectl -n portfolio get endpointslice -l kubernetes.io/service-name=portfolio
curl -fsS https://tom-mendy.com/
```
