# GitHub Actions Runners (ARC)

This directory configures GitHub Actions Runner Controller (ARC) with Argo CD apps:

- `actions-runner-controller` (namespace: `arc-systems`)
- `github-runners-portfolio` (namespace: `arc-runners`)
- `github-runners-dotfiles` (namespace: `arc-runners`)
- `github-runners-sumfeet` (namespace: `arc-runners`)

## 1. Create GitHub auth secret

The runner scale sets read the secret referenced by `githubConfigSecret` in:

- `runner-scale-set-portfolio-values.yaml`
- `runner-scale-set-dotfiles-values.yaml`
- `runner-scale-set-sumfeet-values.yaml`

The preferred path is Infisical. Store the rotated GitHub token in project
`homelab`, env `prod`, path `/github-runners`:

```text
github_token=<rotated-github-token>
sumfleet_github_token=<sumfeet-github-token>
```

The Sumfeet token is mapped to `github_token` in the dedicated Kubernetes
Secret `arc-github-auth-sumfeet`.

Create a Kubernetes Auth machine identity for:

```text
namespace: arc-runners
service account: github-runners-infisical-sync
```

Then enable `kubernetes/github-runners-auth/values.yaml`:

```yaml
infisicalSecret:
  enabled: true
  identityID: "<machine-identity-id>"
```

### Option A: Personal access token (classic)

Manual fallback only. Do not commit real tokens.

```bash
kubectl create secret generic arc-github-auth \
  --namespace arc-runners \
  --from-literal=github_token='<ROTATED_GITHUB_TOKEN>'
```

### Option B: GitHub App

```bash
kubectl create secret generic arc-github-auth \
  --namespace arc-runners \
  --from-literal=github_app_id='<APP_ID>' \
  --from-literal=github_app_installation_id='<INSTALLATION_ID>' \
  --from-file=github_app_private_key='<PATH_TO_PRIVATE_KEY_PEM>'
```

## 2. Confirm target URL

Update `githubConfigUrl` in each values file for your desired scope:

- `runner-scale-set-portfolio-values.yaml`
- `runner-scale-set-dotfiles-values.yaml`
- `runner-scale-set-sumfeet-values.yaml`
- Repository: `https://github.com/<owner>/<repo>`
- Organization: `https://github.com/<org>`
- Enterprise: `https://github.com/enterprises/<enterprise>`

## 3. Deploy via existing GitOps flow

```bash
cd ansible
./run.sh playbooks/deploy-apps.yml
```

## 4. Validate

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get applications -n argocd
kubectl --kubeconfig "$HOME/.kube/config-homelab" get pods -n arc-systems
kubectl --kubeconfig "$HOME/.kube/config-homelab" get pods -n arc-runners
```

If controller logs show `no matches for kind "EphemeralRunnerSet" in version
"actions.github.com/v1alpha1"`, verify CRDs exist:

```bash
kubectl --kubeconfig "$HOME/.kube/config-homelab" get crd | grep actions.github.com
```

Expected CRDs include:

- `autoscalinglisteners.actions.github.com`
- `autoscalingrunnersets.actions.github.com`
- `ephemeralrunners.actions.github.com`
- `ephemeralrunnersets.actions.github.com`

If missing, force re-sync `actions-runner-controller` in Argo CD and
restart the controller pod.

Recommended recovery order:

1. Sync `actions-runner-controller-crds`
2. Sync `actions-runner-controller`
3. Restart controller pod in `arc-systems`
4. Sync `github-runners-portfolio`, `github-runners-dotfiles`, and
   `github-runners-sumfeet`

Use these labels in workflows:

- `runs-on: arc-runner-set-portfolio` for `Tom-Mendy/Portfolio`
- `runs-on: arc-runner-set-dotfiles` for `Tom-Mendy/dotfiles`
- `runs-on: arc-runner-set-sumfeet` for `MrAmarok/sumfeet`
