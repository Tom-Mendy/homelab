# Fix Pangolin restart loop on OVH

## Problem

Pangolin on the OVH VPS was restarting continuously, making the public
Pangolin/Newt entry point unavailable.

## Investigation

The first SSH check used the OVH administration port:

```sh
ssh -F /dev/null -p 2222 debian@92.222.90.223
cd /root/pangolin
docker compose ps
```

The result showed Pangolin in `Restarting (1)` with 1,614 restarts. Its logs
reported:

```text
Error: No configuration file found. Please create one.
```

Docker inspection showed that the running container mounted
`/root/pangolin/config` at `/app/config`, while the complete migrated files
were under `/home/debian/pangolin/config`. The active `/root` directory was
missing `config.yml`, the Traefik files, the certificates, and the Compose
file. The first repair attempt using `cd /root/pangolin` as `debian` failed
with `Permission denied`; no files were changed by that failed command.

The active and migrated SQLite databases were then compared using the
Pangolin image's `better-sqlite3` module. Both passed `PRAGMA integrity_check`,
but their application data differed:

```text
/rootdb/db.sqlite resources=0 sites=0 targets=0
/homedb/db.sqlite resources=17 sites=2 targets=18
```

## Repair commands and results

The active configuration was backed up before modification:

```sh
sudo cp -a /root/pangolin/config /root/pangolin/config.before-restart-20260825-190623
```

The missing configuration and Compose files were restored from the complete
migrated tree, and the complete SQLite database was copied after saving the
empty active database:

```sh
sudo install -m 0644 /home/debian/pangolin/config/config.yml /root/pangolin/config/config.yml
sudo cp -a /home/debian/pangolin/config/traefik /root/pangolin/config/
sudo cp -a /home/debian/pangolin/config/letsencrypt /root/pangolin/config/
sudo cp -a /home/debian/pangolin/config/GeoLite2-Country.mmdb /root/pangolin/config/
sudo install -m 0644 /home/debian/pangolin/docker-compose.yml /root/pangolin/docker-compose.yml
sudo cp -a /root/pangolin/config/db/db.sqlite /root/pangolin/config/db/db.sqlite.before-restore-<timestamp>
sudo cp -a /home/debian/pangolin/config/db/db.sqlite /root/pangolin/config/db/db.sqlite
sudo docker compose -f /root/pangolin/docker-compose.yml up -d
```

The final Compose state was:

```text
gerbil    Up
pangolin  Up (healthy)
traefik   Up
```

Public checks returned HTTP 200 for `pangolin.tom-mendy.com`,
`authentik.tom-mendy.com`, and `forgejo.tom-mendy.com`.

## Final outcome

The Pangolin restart loop was fixed by restoring the missing OVH Compose/config
path and the complete migrated database. The database now contains the
expected public resources and sites. The storage policy check also passed:

```text
./scripts/check-storage-policy.sh
storage policy ok
```

## Docker image refresh

The OVH Compose images were refreshed and the containers were recreated:

```sh
sudo docker compose -f /root/pangolin/docker-compose.yml pull
sudo docker compose -f /root/pangolin/docker-compose.yml up -d
```

The first recreation exposed an identity mismatch: Gerbil restarted with
`failed to parse IP address: invalid CIDR address:`. The restored database
already contained exit node `100.89.128.1/24`, but the key copied from the
migrated tree represented a different Gerbil identity. The key from the
active OVH backup was restored and Gerbil then started normally. Traefik was
started after Gerbil was healthy.

Final validation returned HTTP 200 for Pangolin, Authentik, and Forgejo.
Newt was recreated once after the OVH stack was healthy and reached `1/1
Running`; its logs showed a successful tunnel and all configured targets
healthy. The storage policy check continued to pass.
