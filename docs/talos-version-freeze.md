# Migration version freeze

The image automation hold was applied on 2026-11-07. Both ImageUpdateAutomations
and both ImageRepositories are suspended. A normal reconciliation of the parent
`flux-system` Kustomization completed successfully and preserved the hold.
GitOps controllers and application HelmReleases remain running and unsuspended.
No workload image reference changed during this operation.

The protected objects in `flux-system` are:

| Resource | Name | Original suspend state | Current state |
| --- | --- | --- | --- |
| ImageUpdateAutomation | portfolio | Unset, active | Suspended |
| ImageUpdateAutomation | job-search-manager | True, incident hold | Suspended |
| ImageRepository | portfolio | Unset, active | Suspended |
| ImageRepository | job-search-manager | Unset, active | Suspended |

Each has the live annotation
`kustomize.toolkit.fluxcd.io/reconcile: disabled`. This prevents its parent
Kustomization from overwriting the temporary suspension with old Git state.
The [declarative manifests](../kubernetes/flux/cluster/image-automation.yaml)
also contain the holds, ready for the next reviewed repository update.
Image policies may retain their last results; suspended writers cannot publish
those results to Git. Stopping scanners alone would not be a sufficient hold.
Flux documents [automation suspension][automation] and the
[individual-resource reconciliation guard][guard].

The Flux distribution was independently pinned from `2.9.x` to its already
deployed `2.9.6`, in the live FluxInstance and its
[bootstrap manifest](../kubernetes/flux/bootstrap/flux-instance.yaml).
Controller image references remained unchanged. Retain this exact version after
thawing image automation and schedule Flux upgrades separately.

Private evidence and restoration state are under
`/home/tmendy/.local/state/homelab/talos-migration/20261107T164110Z-version-freeze/`.
The directory is owner-only and must stay outside Git. Important records are:

- `resume-state.json`: original suspend fields, reconciliation guards, and UIDs.
- `baseline.json`: 74 controller image inventories, 41 Helm chart selections,
  observed runtime image IDs, and Git artifact revisions.
- `cutover-image-catalog.json`: active container references and observed pullable
  runtime digests for per-application cutover preparation.
- `parent-reconcile-after.json`: successful parent reconciliation after the hold.
- `freeze-check.json`: current hold and baseline-drift verdict.
- `flux-distribution-pin.json`: the unchanged deployed Flux release and new pin.

The recorded root source revision is
`82784a0841c1f744f1031424d7afeab00f9a8c1c`. This is the observed cluster source,
not a claim that uncommitted preparation files were deployed. Git advanced from
the initial inventory revision during preparation without changing workload
images. The final strict check reported no drift from the saved freeze baseline.
The root source still follows main; its final maintenance commit must be fixed
after the reviewed preparation changes have been committed and reconciled.

Use the read-only check before maintenance:

```sh
python3 scripts/migration-version-freeze.py check --strict-baseline \
  --state /private/version-freeze-state
```

The checker fails on an unprotected or active image writer/scanner, an in-flight
image reconciliation, inventory changes, a floating Flux distribution, or strict
baseline drift. It does not suspend applications or apply a maintenance profile.
`maintenance_window_ready` deliberately remains false because the remaining
publisher, source, and image-digest gates need separate verification.
Re-running `freeze` with the same state directory preserves the original resume
record and baseline. Use a new state directory only for a newly reviewed window
baseline; never overwrite the November resume record to hide drift.

The image hold does not prevent manual commits, direct Helm upgrades, Coder
template publication, or registry tag replacement. The active Pod inventory has
57 tag-only image occurrences, including init containers and infrastructure.
The catalog has 104 observed pullable runtime digests among 131 occurrences;
some completed or unstarted init containers have no runtime image ID. Do not
invent a digest for those entries. Before an application's final cutover, resolve
and verify its immutable references and use them for the target. Do not roll out
every Ubuntu application just to rewrite image references during preparation.

The repository image checker reports suggestions and does not write updates.
The publication workflows can push registry tags. In particular,
`.forgejo/workflows/publish-coder-templates.yml` can directly publish templates
to Coder; suspension of Flux image automation does not control that path.
Portfolio and job-search-manager already use digest-pinned application images,
so updating their `latest` registry tags alone does not change their deployments.

Complete these gates in the maintenance window:

1. Commit and review the final preparation changes, reconcile them, and capture
   a new approved Git/image/chart baseline while preserving the original resume
   record. Review every difference from the November baseline explicitly.
2. Apply the [capacity runbook](talos-node2-capacity.md): block new CI intake,
   drain active jobs, hold both GitHub runner pools at zero, and stop the four
   Forgejo runners. Prevent manual publication and stop Coder template/image
   publishing jobs before restarting or stopping workspaces. No active publisher
   may be left running against production during the window.
3. Fix the Ubuntu root GitRepository to the approved commit. Save its original
   `spec.ref` first. Because FluxInstance generates that source, save and
   temporarily disable the instance's own reconciliation with
   `fluxcd.controlplane.io/reconcile: disabled` before setting
   `GitRepository/flux-system.spec.ref.commit`. Keep the Flux controllers
   running. A commit takes precedence over branch/name refs. Do not assume a
   runtime GitRepository edit survives its owning operator without this guard.
   See [FluxInstance reconciliation][instance] and [Git commit references][git].
4. Verify the source artifact and Kustomization applied revision both match the
   approved commit. Capture and compare the actual Helm chart revisions and
   source artifacts. All current chart selectors are exact versions, but do not
   permit registry/chart replacement or release changes during the window.
   If needed, suspend and guard the affected HelmRepository/OCIRepository sources
   after saving their state; leave their current artifacts available.
5. Check the image hold and retained application digests again. Intentional
   capacity pauses remove some Pods and Coder Deployments, so strict whole-cluster
   drift can report those removals. Record the planned pause set and compare
   retained applications against their original catalog; do not automatically
   accept a new image just because a Pod was recreated.
6. Abort the next migration operation if an unexpected Git/chart/image version
   appears. Identify the writer and restore the approved artifact or deliberately
   review a new baseline before proceeding. Keep the final cutover backups paired
   with their recorded application versions.

Thaw only when the migration window is closed and capacity permits CI again:

1. Review pending image-policy results before re-enabling writers; a queued
   digest change may publish immediately. Restore CI and template publishing
   separately, one service at a time.
2. Update the Git image-automation manifests to their intended post-window
   states. Portfolio's writer and both scanners may return to active. Keep the
   job-search-manager writer suspended until its original failing-image incident
   is resolved separately. Do not use a blanket resume-all command.
3. With the FluxInstance still guarded, restore the saved root Git source ref,
   then restore its owner's original reconciliation annotation. Restore any
   separately held chart sources from their own saved states. Verify the desired
   manifest revision is the reviewed thaw revision before removing image holds.
4. Restore the four image resource states using the original resume record:

   ```sh
   python3 scripts/migration-version-freeze.py restore \
     --state /private/version-freeze-state
   ```

   The helper validates every saved UID and current hold before resuming any
   object. It restores the recorded suspend fields before removing guards.
   Tests cover preservation of the pre-existing incident hold, refusal to thaw a
   replaced resource or another cluster, and baseline preservation on re-freeze.
5. Reconcile and verify the intended Git states, healthy applications, and actual
   execution of newly admitted CI jobs. The image restore helper does not restore
   runner replicas, Coder workspaces, or the separate window source/owner guards.

See [the migration tracker](talos-migration.md). The automation hold is active;
the complete maintenance-window freeze remains conditional on the gates above.

[automation]: https://fluxcd.io/flux/components/image/imageupdateautomations/
[guard]: https://fluxcd.io/flux/components/kustomize/kustomizations/
[instance]: https://fluxoperator.dev/docs/crd/fluxinstance/
[git]: https://fluxcd.io/flux/components/source/gitrepositories/
