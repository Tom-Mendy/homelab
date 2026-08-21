# Enable Grafana Authentik auto-login

## Problem

Opening Grafana from the Authentik application dashboard still showed the
Grafana login page, requiring a second click on the Authentik login button.

## Reasoning and investigation

The Grafana application in the Authentik blueprint launches the Grafana root
URL. Grafana then sends an unauthenticated browser to `/login`. The requested
behavior requires Grafana to redirect that login page to its configured OAuth
provider automatically.

The live HTTP behavior reproduced the report:

```text
$ curl -ksS -D - -o /dev/null https://grafana.home.tom-mendy.com/
HTTP/2 302
location: /login

$ curl -ksS -D - -o /dev/null https://grafana.home.tom-mendy.com/login
HTTP/2 200
```

The same check was run as an assertion. It failed because the second request
did not redirect to `/login/generic_oauth`:

```text
GET /      -> /login
GET /login -> <none>
FAIL: Grafana still displays its local login page
```

The running Grafana configuration confirmed that `[auth.generic_oauth]` did
not contain `auto_login`. The deployed Helm manifest showed the same result.
The command below only printed non-secret OAuth settings:

```sh
kubectl -n grafana exec deploy/grafana -- \
  sh -c "sed -n '1,35p' /etc/grafana/grafana.ini"
```

The Grafana 12.4.1 chart was rendered with the repository values. The rendered
configuration included the expected setting:

```text
[auth.generic_oauth]
auto_login = true
```

This confirmed that the key is supported and is in the correct values path.

## Change

Grafana's Generic OAuth configuration now enables `auto_login`. Grafana will
redirect directly to Authentik when its login page is opened, so launching the
Grafana application from Authentik starts the SSO flow automatically.

The change was made in:

```text
kubernetes/grafana/values.yaml
```

## Validation

```sh
helm lint /home/tmendy/.cache/helm/repository/grafana-12.4.1.tgz \
  -f kubernetes/grafana/values.yaml
helm template grafana /home/tmendy/.cache/helm/repository/grafana-12.4.1.tgz \
  -f kubernetes/grafana/values.yaml
helm lint kubernetes/grafana
git diff --check
./scripts/check-storage-policy.sh
rumdl check --fix \
  docs/activity_report/2026-08-21-grafana-authentik-auto-login/2026-08-21-grafana-authentik-auto-login.md
```

The official chart lint, local chart lint, rendered configuration assertion,
Git whitespace check, storage policy check, and activity report Markdown check
passed. The repository-wide `rumdl check --fix .` command also ran but found
136 pre-existing issues in 17 other files. The live HTTP assertion failed
before reconciliation, as expected, because the running pod still used the old
configuration.

## Outcome

The repository now contains the Grafana auto-login setting. After the
`grafana` HelmRelease reconciles and Grafana restarts, opening the Grafana
application from Authentik will automatically start the Authentik OAuth flow
instead of requiring a click on the Grafana login button.
