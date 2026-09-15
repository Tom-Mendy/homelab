# Migrate Hermes and Hindsight data to the cluster

## Problem

Hermes was running on `hstgr` with persistent memories and locally created
skills. Hindsight stored its data in a separate embedded PostgreSQL volume on
the old host. The goal was to move those data into the existing NFS-backed
cluster workloads without replacing the cluster configuration, secrets, or
Matrix state.

## Reasoning and commands

The repository already provided NFS-backed PVCs for both workloads:

```console
$ kubectl get pvc -n coder-workspaces
coder-9a2cfda8-92a2-4f7e-ac1b-6fa54ee48ccc-hermes   Bound   ...   20Gi   nfs-k8s

$ kubectl get pvc -n agent
hindsight-data   Bound   ...   10Gi   nfs-k8s
```

The first network attempt from the restricted environment failed:

```text
Temporary failure in name resolution
Unable to connect to the server: socket: operation not permitted
```

After approved network access, the source inventory showed:

```text
/home/hermes/.hermes/memories       12K
/home/hermes/.hermes/skills         21M
/home/hermes/.hermes/hindsight      8.0K
/home/hermes/.hermes/state.db       53M
/home/hermes                         7.2G
```

The Hindsight PostgreSQL data was not under `/home/hermes`. Docker showed the
real source volume:

```text
ghcr.io/vectorize-io/hindsight:latest  hindsight
Source: /var/lib/docker/volumes/hindsight_hindsight-pg0/_data
Destination: /home/hindsight/.pg0
Image version: 0.7.2
```

The target image was the pinned 0.6.1 API image. PostgreSQL migration versions
also differed:

```text
source: c1d2e3f4a5b6
target: m3rg3h3ad5f6
```

Replacing the target `.pg0` directory was therefore rejected as unsafe. The
Hindsight API was used instead. The source bank had 26 documents, 35 memory
nodes, and 728 links; the target bank was `hermes` and already contained two
nodes.

Before copying, both Hermes gateways were stopped and the target memories,
skills, and Hindsight API data were backed up locally:

```console
$ sha256sum /tmp/hermes-migration.uJcHDt/*
fe426d153dea6a1607dc53712762e8295e851865db77c0c9d5c1a74dd74cf6e5  hermes-target-before.tgz
1ef6a1db695fd7a5f85aad5376688fd46e4603fa61122e7871ca3162c03621f7  hindsight-target-documents.json
d9cbff65d7b91cabee873957dbf62fb2af072169b5dbcf2b4619d2eca36d6094  hindsight-target-memories.json
```

Only Hermes built-in memory files and locally managed skills were transferred.
Configuration, `.env`, authentication, sessions, caches, Matrix crypto state,
and the 53 MiB Hermes state database were excluded.

The first Hindsight payload used `text` instead of the API's `original_text`
field and was rejected before any write:

```text
HTTP 422: body.items.0.content — Input should be a valid string
```

The corrected payloads were submitted with `async=true`. A synchronous attempt
was stopped after it remained in Ollama extraction for more than ten minutes;
it created no document. The asynchronous API then accepted all 26 documents.

## Results

Hermes memory hashes match the source exactly:

```text
1ffb10a25fd751de22b0a939c6d846f62fdb24ba7b5f26a1966470d4916b9765  MEMORY.md
6357e32b4bb98ba6abffbd273c5c25967aff2f0e025a8e974c0fc97f4a825f96  USER.md
```

Hermes reports the external provider and local skills correctly:

```text
Provider:  hindsight
Plugin:    installed ✓
Status:    available ✓
0 hub-installed, 0 builtin, 11 local — 11 enabled, 0 disabled
```

Hindsight reports a healthy database. The 26 source documents were imported
alongside the one document that already existed in the target bank:

```json
{"status":"healthy","database":"connected"}
{"total_documents":27,"total_nodes":68,"total_links":1520}
```

The import operations completed with zero failures. Hindsight continued
automatic consolidations in the background after the document imports; this is
normal provider work and does not block Hermes operation.

The running Hermes and Hindsight workloads remained on NFS-backed PVCs. No
repository manifest or storage configuration was changed. An unrelated
`hindsight-control-plane` pod was already in `CreateContainerConfigError`; it
was not modified because the API workload remained healthy and it was outside
the data transfer scope.

## Final outcome

Hermes `MEMORY.md`, `USER.md`, and locally managed skills were migrated to the
cluster PVC. Hindsight's 26 source documents were re-ingested through its API,
which regenerated embeddings and graph links safely across the differing
PostgreSQL schemas. Configuration, credentials, Matrix state, and unrelated
Hermes runtime data were preserved.
