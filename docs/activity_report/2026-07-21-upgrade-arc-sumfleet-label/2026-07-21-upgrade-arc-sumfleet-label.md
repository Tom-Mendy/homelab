# Upgrade ARC and separate the Sumfleet runner name from its label

<!-- rumdl-disable MD013 -->

Date: 2026-07-21

## Problem

The runners for `MrAmarok/sumfeet` needed the scale set name
`arc-runner-set-sumfleet-tom` while retaining the GitHub Actions label
`self-hosted`.

ARC chart 0.13.1 only rendered `runnerScaleSetName`; it ignored a separate
label value. ARC 0.14.2 adds `scaleSetLabels` to the Helm values and renders it
as `spec.runnerScaleSetLabels`. The shared controller and all managed scale
sets therefore had to be upgraded together.

## Reasoning and changes

The upgrade used a coordinated maintenance window because ARC runners are
ephemeral and the official upgrade procedure requires removing scale sets
before replacing the controller.

The repository changes were:

- Pin the CRDs to `gha-runner-scale-set-0.14.2` instead of `master`.
- Upgrade the controller, Dotfiles, Portfolio, and Sumfeet applications from
  chart 0.13.1 to 0.14.2.
- Add Argo CD cascade finalizers to the controller and the three managed scale
  set Applications.
- Set the Sumfeet scale set name to `arc-runner-set-sumfleet-tom`.
- Set its only additional routing label to `self-hosted`.
- Keep the repository URL, Infisical Secret, DinD mode, autoscaling limits,
  and runner resources unchanged.

The final Sumfeet values are:

```yaml
runnerScaleSetName: "arc-runner-set-sumfleet-tom"

scaleSetLabels:
  - self-hosted
```

## Preflight and rendering

No ephemeral runner or runner pod was active before maintenance:

```console
$ kubectl get ephemeralrunners -n arc-runners
No resources found in arc-runners namespace.

$ kubectl get pods -n arc-runners
No resources found in arc-runners namespace.
```

All existing ARC Applications were healthy. The CRD Application was already
`OutOfSync` because its floating `master` source was ahead of the installed
CRDs:

```console
actions-runner-controller        Synced      Healthy
actions-runner-controller-crds   OutOfSync   Healthy
github-runners-auth              Synced      Healthy
github-runners-dotfiles          Synced      Healthy
github-runners-portfolio         Synced      Healthy
github-runners-sumfeet           Synced      Healthy
homelab                          Synced      Healthy
```

The 0.14.2 charts rendered successfully with these immutable OCI digests:

```console
gha-runner-scale-set-controller:0.14.2
sha256:3081ba15c41f0aa791058dedd2a7406fece24c9aeaa94956c268e5099427a452

gha-runner-scale-set:0.14.2
sha256:579e3a1bdf4032b3c3de3e9b0880a4a6d3c1989a67c06010f680c1cc49524d11
```

The rendered Sumfleet resource contained:

```yaml
githubConfigUrl: https://github.com/MrAmarok/sumfeet
githubConfigSecret: arc-github-auth-sumfeet
runnerScaleSetName: arc-runner-set-sumfleet-tom
runnerScaleSetLabels:
  - self-hosted
maxRunners: 5
minRunners: 0
```

### Useful failed checks

The initial Sumfleet server dry-run failed because the live CRD did not yet
contain the new field:

```console
Error from server (BadRequest): AutoscalingRunnerSet in version "v1alpha1"
cannot be handled as a AutoscalingRunnerSet: strict decoding error:
unknown field "spec.runnerScaleSetLabels"
```

The first CRD server-side dry-run also reported field ownership conflicts
because Argo CD owns `.spec.versions`:

```console
Apply failed with 2 conflicts: conflicts with "argocd-controller":
- .metadata.annotations.controller-gen.kubebuilder.io/version
- .spec.versions
```

Using Argo CD's existing field manager proved that the tagged CRDs were valid
without taking ownership away from Argo CD:

```console
$ kubectl apply --server-side --dry-run=server \
    --field-manager=argocd-controller \
    -f charts/gha-runner-scale-set-controller/crds
customresourcedefinition.apiextensions.k8s.io/autoscalinglisteners.actions.github.com serverside-applied (server dry run)
customresourcedefinition.apiextensions.k8s.io/autoscalingrunnersets.actions.github.com serverside-applied (server dry run)
customresourcedefinition.apiextensions.k8s.io/ephemeralrunners.actions.github.com serverside-applied (server dry run)
customresourcedefinition.apiextensions.k8s.io/ephemeralrunnersets.actions.github.com serverside-applied (server dry run)
```

The CRD diff showed the expected additive field:

```diff
+ runnerScaleSetLabels:
+   items:
+     type: string
+   type: array
```

Controller, Portfolio, and Dotfiles passed Kubernetes server dry-runs before
the maintenance. The Sumfleet server dry-run was deferred until the CRD wave
installed the additive field.

## Maintenance execution

The root Application was suspended before pushing commit `9272f59`:

```console
$ kubectl patch application homelab -n argocd --type=merge \
    -p '{"spec":{"syncPolicy":{"automated":{"enabled":false}}}}'
application.argoproj.io/homelab patched
```

Cascade finalizers were applied to the running child Applications, then the
three managed scale sets were deleted in this order:

1. `github-runners-sumfeet`
2. `github-runners-portfolio`
3. `github-runners-dotfiles`

Each Application and its `AutoscalingRunnerSet` disappeared before the next
one was removed.

The teardown check found an older orphaned `arc-runner-set` for
`Tom-Mendy/homelab`. Its tracking annotation referred to the removed
`github-runners` Application, which no longer exists in the repository. It had
no active job and was deleted so that every 0.13.1 scale set was absent before
the controller upgrade:

```console
$ kubectl delete autoscalingrunnerset arc-runner-set -n arc-runners
autoscalingrunnerset.actions.github.com "arc-runner-set" deleted
```

Its listener and ephemeral runner set were cleaned automatically. The
controller Application was then removed, and the following check returned no
ARC workload resources:

```console
$ kubectl get autoscalingrunnersets,autoscalinglisteners,ephemeralrunnersets,ephemeralrunners -A -o name
# no output

$ kubectl get deployment arc-gha-rs-controller -n arc-systems
Error from server (NotFound): deployments.apps "arc-gha-rs-controller" not found
```

The CRDs, `github-runners-auth`, `arc-github-auth`, and
`arc-github-auth-sumfeet` remained present.

The root Application was re-enabled and refreshed. Sync waves installed the
tagged CRDs, controller 0.14.2, and all three scale sets:

```console
attempt=4 root=Synced/Healthy/Succeeded controller=Synced/Progressing sumfeet=OutOfSync/Healthy
attempt=5 root=Synced/Healthy/Succeeded controller=Synced/Healthy sumfeet=Synced/Healthy
```

## Final validation

All ARC Applications are healthy and use 0.14.2:

```console
actions-runner-controller        Synced   Healthy   0.14.2
actions-runner-controller-crds   Synced   Healthy
github-runners-auth              Synced   Healthy
github-runners-dotfiles          Synced   Healthy   0.14.2
github-runners-portfolio         Synced   Healthy   0.14.2
github-runners-sumfeet           Synced   Healthy   0.14.2
homelab                          Synced   Healthy
```

The controller and scale sets report:

```console
arc-gha-rs-controller   1   ghcr.io/actions/gha-runner-scale-set-controller:0.14.2

arc-runner-set-dotfiles       0   5   https://github.com/Tom-Mendy/dotfiles    <none>
arc-runner-set-portfolio      0   5   https://github.com/Tom-Mendy/Portfolio   <none>
arc-runner-set-sumfleet-tom   0   5   https://github.com/MrAmarok/sumfeet      [self-hosted]
```

The Sumfleet listener is registered:

```console
arc-systems   arc-runner-set-sumfleet-tom-fc6cdddb-listener   arc-runner-set-sumfleet-tom
```

Infisical reconciliation succeeded, and the dedicated Kubernetes Secret
contains only the expected key without displaying its value:

```console
LastReconcileStatus=True   Reconciliation successful

$ kubectl get secret arc-github-auth-sumfeet -n arc-runners \
    -o go-template='{{range $k,$v := .data}}{{$k}{{"\\n"}}{{end}}'
github_token
```

## GitHub Actions acceptance test

The repository workflows already use `runs-on: [self-hosted]`, but none has a
`workflow_dispatch` trigger. To avoid pushing an artificial commit or running
a release workflow, the previously successful Playwright run `29840702529`
was rerun through the GitHub API:

```console
rerun_http_code=201
attempt=2 run=2/queued/ runners=arc-runner-set-sumfleet-tom-s64w5-runner-md6px
attempt=3 run=2/in_progress/ runners=arc-runner-set-sumfleet-tom-s64w5-runner-md6px
attempt=21 run=2/completed/success runner_count=1
```

GitHub reported the final job routing:

```console
test   completed   success   arc-runner-set-sumfleet-tom-s64w5-runner-md6px   self-hosted
```

A second Playwright job already queued for pull request 300 was assigned to
another runner after the listener came online. Its routing was correct, but
the application test itself failed:

```console
test   completed   failure   arc-runner-set-sumfleet-tom-s64w5-runner-6jxx9   self-hosted
failed-step   Run Playwright tests   failure
```

This failure was unrelated to ARC. After both jobs completed, all Sumfleet
`EphemeralRunner` resources were removed and controller logs contained no
errors during the final three-minute window.

## Final outcome

ARC 0.14.2 is deployed consistently. Sumfeet runners are registered under
`arc-runner-set-sumfleet-tom`, accept jobs labeled `self-hosted`, scale from
zero to five, and return to zero after jobs finish. Portfolio and Dotfiles kept
their existing names and routing behavior. No persistent storage or
`local-path` dependency was introduced.
