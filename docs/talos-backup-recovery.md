# Talos migration backup and recovery record

The migration backup set completed on 2026-11-07. Application recovery
data is copied to the NixOS workstation, independently of Kubernetes and the
Synology. The migration tracker remains the authority for the step 1 gate.

Private evidence and encrypted backups are under
`/home/tmendy/.local/state/homelab/talos-migration/20261107T110801Z-data/`.
The directory is owner-only. The separate age recovery identity is
`/home/tmendy/.config/homelab-recovery/talos-20261107.agekey`, mode 0600.
Never commit that identity, decrypted exports, or private evidence to Git.
The identity and backup set are on the same workstation. This is not an
off-site backup, and losing both loses this recovery copy.

Completed recovery evidence:

- All six CloudNativePG application databases have successful logical restore
  tests, including the repaired Authentik database. Their encrypted copies were
  compared with the checksums of the restore-tested originals.
- Atuin PostgreSQL 16, Harbor PostgreSQL 18, and Hindsight PostgreSQL 18 dumps
  restored successfully. Hindsight retained all four extensions and 25 tables,
  including one bank, 51 documents, and 1,274 memory units. A vector operation
  succeeded for all 1,274 populated embeddings. LLM recall was not tested.
- Forgejo, Open WebUI, Infisical, Hindsight, Atuin, and Harbor additionally passed
  restoration of database roles, object ownership, and grants. Forgejo and
  Open WebUI have database snapshots paired with stopped-writer file snapshots.
- Coder and job-search-manager also passed complete role, ownership, and grant
  restoration. Their escrowed database passwords authenticated against isolated
  servers using SCRAM. Deliberately incorrect passwords were rejected.
- The encrypted configuration archive contains 288 Kubernetes Secrets, workload
  configuration, cluster access objects, storage bindings, kubeconfig, and the
  existing Talos preparation files. It passed decryption and archive readback.
  PostgreSQL global role definitions and Hindsight pg0 bootstrap configuration
  are protected separately in the same encrypted backup set.
  A separate archive retains the three schema-validated Talos candidate files
  and explicit Ubuntu kubeconfig context. Installation disks remain placeholders
  pending physical inspection; schema validation is not installation approval.
- The escrowed Infisical encryption key decrypted the restored database's KMS
  root, two internal keys, the project data key, and all 92 secret values.
  Values were not printed or saved in test output. A wrong-key negative control
  failed as expected. This does not prove UI, SSO, or new-cluster identity login.
- Garage was stopped with its application writer and scheduled object backup
  suspended. The complete node archive includes LMDB metadata, blocks, node
  identity, layout, and permissions. The original 2.4.1 image opened the restored
  node with networking disabled. Bucket metadata matched, and all 29 current
  objects were read through S3 and matched production content checksums.
  All 29 document versions referenced by the restored job-search database also
  matched those objects' stored hashes and byte counts.
- Tuwunel was stopped for its complete data snapshot. The original 1.9.4 image
  opened the restored RocksDB and served the Matrix client versions endpoint
  with networking, federation, and registration disabled. SSO and federation
  were not tested against the restored copy.
- Infisical Redis and Harbor Valkey replication snapshots passed their native
  RDB checkers, loaded into isolated servers, and answered PING. No restored
  consumer was connected to production. Final cutover still requires a producer
  drain and an explicit decision about replaying queued work.
- Prowlarr's active database had a damaged history index and freelist. An
  offline REINDEX followed by VACUUM INTO produced an integral replacement.
  All 21 tables, their complete row fingerprints, and the schema matched the
  original. The original database and pre-repair files are retained. Fresh
  Prowlarr, Radarr, and Sonarr native ZIP backups passed SQLite integrity checks.
- Grafana, Navidrome, and the repaired native media backups passed full archive
  readback and SQLite checks. Vaultwarden and VPN state snapshots passed
  filesystem restoration and SQLite checks. Traefik's ACME JSON was read back
  and parsed successfully without interrupting ingress.
- Forgejo's complete file archive was extracted and all seven restored Git
  repositories passed `git fsck --full`. Open WebUI's complete file archive and
  qBittorrent configuration were extracted and their SQLite databases checked.
- The stopped-writer Prometheus snapshot was extracted, opened by the exact
  production image in an isolated container, and queried successfully for
  historical `up` samples. Its test configuration had no scrape targets.
- The durable Desktop and Hermes workspace snapshots passed integrity checks
  for their 12 selected application SQLite databases, including associated WAL
  files. This does not prove that the workspace runtimes start from a clone.
- NZBGet's queue and incoming-NZB directories were captured separately while
  its writer was stopped. Both directories were empty at snapshot time. Their
  archives passed extraction checks alongside the configuration snapshot.

The final `manifest.json` records 55 encrypted archives, ciphertext checksums,
evidence references, and recovery coverage or explicit exclusions for 43 source
volumes. `coordinator-verified-archives.json` records successful complete archive
checks for all 11 queued snapshots, including the three durable workspace PVCs.
Harbor's 2,044 stored blobs and Ollama's 18 stored blobs matched the SHA-256
encoded in their filenames. These online artifact baselines passed content
checks; no complete Harbor or Ollama runtime startup is claimed by that test.
A staged archive or a `.complete.json` transport marker alone is not a
successful application recovery test.

The repaired Prowlarr native backup is the recovery source. The encrypted
pre-repair snapshot and diagnostic working-file archive deliberately preserve
damaged historical databases for investigation and must not replace production.
Diagnostic working files were compared byte-for-byte after encryption and
decryption before their plaintext copies and restore-test scratch trees were
removed. The earlier Authentik evidence directory remains preserved.

Temporary plaintext NFS staging, helper Pods, namespace, staging PVC, and its
released PV were removed after verification. Production source volumes were
mounted read-only and were not deleted. An empty Retain-policy staging directory
may remain on Synology. `temporary-staging-cleanup.json` records the cleanup.
All 40 saved writer, reconciliation, and scheduled-job settings matched their
original state. All three nodes and six CNPG instances were Ready, every
Deployment and StatefulSet had its desired replicas, and no HelmRelease was
suspended. No temporary local restore containers remained.

For mutable application files, stop the writer and suspend only the relevant
reconciliation while creating an immutable archive on shared `nfs-k8s` staging
storage. Resume the service after the snapshot completes. Production volumes
are mounted read-only by the backup helper. Downloads happen after service
resumption, verify the source size and SHA-256, and are encrypted with age.
Interrupted downloads retain an owner-only temporary prefix and resume from
that offset. The plaintext temporary file is removed after encryption.

Unframed Kubernetes exec transfers were found to return partial output,
occasionally with a successful exit code. This is why exit status and successful
age encryption are insufficient checks. The replacement transfer protocol
checks source bytes and fingerprints before accepting a copy. The verifier also
consumes the gzip trailer instead of stopping at tar end-of-archive.
For the fixed Harbor and Ollama volume layouts, it also checks each stored blob
against the SHA-256 encoded in its filename. A changed-byte regression fixture
was rejected even though its archive and encryption were valid.

The local supervisor was `homelab-talos-backups.service` and exited successfully.
Its private log and resume records are in the evidence directory.
Remote snapshot creation survives
a dropped exec connection. The supervisor observes completion before restoring
replicas and reconciliation. If stopping it during maintenance, verify every
saved `*-resume-state.json` against the live cluster before leaving the task.

To verify a backup without exposing its contents:

```sh
nix shell nixpkgs#age nixpkgs#python3 --command \
  python3 scripts/verify-migration-backup.py \
  /path/to/backup.tar.gz.age \
  --identity /path/to/recovery.agekey
```

For a real extraction and SQLite test, use a new empty directory:

```sh
nix shell nixpkgs#age nixpkgs#python3 --command \
  python3 scripts/verify-migration-backup.py \
  /path/to/backup.tar.gz.age \
  --identity /path/to/recovery.agekey \
  --extract-to /private/empty-restore-directory --check-sqlite
```

The same command supports `.zip.age` native media backups. It rejects a valid
encrypted file with a truncated gzip payload and a valid ZIP containing the
historical corrupted Prowlarr database. These regression cases were executed.
Failed extraction leaves scratch files for inspection. Never use a partially
extracted directory as a recovery source.

For production recovery, restore into a new `nfs-k8s` PVC, preserve archive
ownership and modes, and reconstruct the matching configuration and credentials.
Restore PostgreSQL roles before their owned objects, adapting operator-managed
roles to the new cluster rather than replacing a live cluster's global roles.
Validate the isolated copy before changing an application's claim or traffic.
Never start two writers against the same NFS application directory.
Use Git for desired configuration. Exported Kubernetes UIDs, resource versions,
service-account tokens, cluster CA data, and Helm histories are evidence, not a
bundle to apply wholesale to Talos. Let the new cluster issue runtime credentials
and reconfigure Infisical's Kubernetes authentication for its issuer and CA.

This set covers application state, configuration, and recovery credentials.
The fixed NAS music, film, series, and download libraries are separate datasets
and are not copied by this procedure. Trivy vulnerability databases and build
caches can be regenerated. Ephemeral workspace runtime data is not a durable PVC
backup; close or export unfinished sessions before their node is migrated.
No Synology snapshot or off-site media backup is claimed here.

See [the migration tracker](talos-migration.md),
[storage recovery](kubernetes-storage.md), and
[Authentik task-log recovery](authentik-tasklog-recovery.md).
