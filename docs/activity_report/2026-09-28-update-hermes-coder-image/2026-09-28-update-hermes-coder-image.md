# Update Hermes image used by the Coder workspace

## Problem

The `hermes-personal` Coder template pinned the Hermes image to the older
`v2026.7.1` digest. Hermes updates are performed by replacing the container
image; `hermes update` cannot update an image-based workspace in place.

## Discovery

Docker Hub reports the newer stable tag `v2026.9.24`. The amd64 image digest
is:

```text
sha256:2fd023efbb8d3d2b0ce1a73d028b07370cff34f567cfe0e999553e8c327ea283
```

The workspace PVC remains mounted at `/opt/data`, so Hermes configuration and
session data persist across the image replacement.

## Changes

`kubernetes/coder/workspace-templates/hermes-personal/main.tf` now uses the
pinned `v2026.9.24` amd64 digest and updates the runtime virtual-environment
constraint filename from `v2026.7.1` to `v2026.9.24`.

The persistent model configuration was not overwritten. Selecting
`gpt-6-luna` still depends on the provider exposing that model and on valid
provider authentication inside the workspace.

## Validation

Run Terraform formatting and validation before pushing the template:

```sh
terraform fmt -check
terraform init -backend=false
terraform validate
```
