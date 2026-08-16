# Fix Open WebUI login (pydantic validation error on signin)

## Problem

Signing in to Open WebUI at `openwebui.home.tom-mendy.com` with the admin
account (`nainjoueur64@gmail.com`) failed. The pod itself was healthy:

```sh
kubectl -n openwebui get pods,pvc -o wide
```

```text
NAME           READY   STATUS    RESTARTS   AGE   NODE
open-webui-0   1/1     Running   0          26h   node3

NAME         STATUS   VOLUME     ...   STORAGECLASS
open-webui   Bound    pvc-...    ...   nfs-k8s
```

## Reasoning path

The failure showed up as an HTTP 500 inside the backend, not as a Kubernetes
crash. Checking the pod logs:

```sh
kubectl -n openwebui logs open-webui-0 --tail=100
```

The important part was a `pydantic` traceback from the signin handler:

```text
File "/app/backend/open_webui/routers/auths.py", line 663, in signin
    user = await Auths.authenticate_user(
File "/app/backend/open_webui/models/users.py", line 341, in get_user_by_email
    return UserModel.model_validate(match)
pydantic_core._pydantic_core.ValidationError: 1 validation error for UserModel
settings
  Input should be a valid dictionary or instance of UserSettings
  [type=model_type, input_value='{"ui": {"version": "0.6.9"}}', input_type=str]
```

So `get_user_by_email` returned a row whose `settings` column was a string
instead of a dict, and pydantic refused to build a `UserModel` from it. The
login request therefore never reached the password check.

Inspecting the SQLite database inside the pod:

```sh
kubectl exec -n openwebui open-webui-0 -- python -c '
import sqlite3
con = sqlite3.connect("/app/backend/data/webui.db")
cur = con.cursor()
cur.execute("SELECT id, info, settings FROM user")
for r in cur.fetchall():
    print("info raw=   ", repr(r[1]))
    print("settings raw=", repr(r[2]))
cur.execute("SELECT sql FROM sqlite_master WHERE type=table AND name=user")
print(cur.fetchall()[0][0])
'
```

Result:

```text
id= 3ac9f049-f82d-4145-b323-3905903268ee
info raw=    'null'
settings raw= '"{\\"ui\\": {\\"version\\": \\"0.6.9\\"}}"'
```

```sql
CREATE TABLE "user" (
    ...
    info JSON,
    settings JSON,
    ...
)
```

The `settings` column was double-encoded: the stored text is the JSON
representation of a string containing JSON, i.e. `"{"ui": ...}"` instead of the
object `{"ui": ...}`. This is a known upstream bug
(open-webui/open-webui#26403): migration `b10670c03dd5` writes
`json.dumps(parsed)` into an `sa.JSON()` column on SQLite, so the driver
serializes it a second time. Databases with exactly one user migrate without
crashing but get this silent double-encoding. On login the backend reads the
value back as a `str`, and pydantic validation fails.

## Commands and results

Back up the database first:

```sh
kubectl exec -n openwebui open-webui-0 -- sh -c \
  'cd /app/backend/data && cp webui.db webui.db.bak-$(date +%F) && ls -la webui.db*'
```

```text
-rw-r--r-- 1 root root 643072 Jun 27 08:36 webui.db
-rw-r--r-- 1 root root  32768 Aug 10 13:03 webui.db-shm
-rw-r--r-- 1 root root      0 Aug 10 13:03 webui.db-wal
-rw-r--r-- 1 root root 643072 Aug 11 15:41 webui.db.bak-2026-08-11
```

Rewrite the corrupted `settings` cell as a single-encoded JSON object:

```sh
kubectl exec -n openwebui open-webui-0 -- python -c '
import sqlite3, json
con = sqlite3.connect("/app/backend/data/webui.db")
con.execute("UPDATE user SET settings = ? WHERE id = ?",
    (json.dumps({"ui": {"version": "0.6.9"}}), "3ac9f049-f82d-4145-b323-3905903268ee"))
con.commit()
row = con.execute("SELECT settings FROM user WHERE id = ?",
    ("3ac9f049-f82d-4145-b323-3905903268ee",)).fetchone()
print("stored:", repr(row[0]))
'
```

```text
stored: '{"ui": {"version": "0.6.9"}}'
```

Verify using the application's own ORM read path (the same code signin uses).
A raw `sqlite3` read does not deserialize JSON columns, so it is not a valid
verification; `Users.get_user_by_email` goes through SQLAlchemy:

```sh
kubectl exec -n openwebui open-webui-0 -- sh -c \
  'WEBUI_SECRET_KEY=verify-only python -c "
import asyncio
from open_webui.models.users import Users
u = asyncio.run(Users.get_user_by_email(\"nainjoueur64@gmail.com\"))
print(\"VALIDATED OK:\", u.email, \"| settings type:\", type(u.settings).__name__)
print(\"settings:\", u.settings)
print(\"info type:\", type(u.info).__name__, u.info)
"'
```

```text
VALIDATED OK: nainjoueur64@gmail.com | settings type: UserSettings
settings: ui={'version': '0.6.9'}
info type: NoneType None
```

Confirm the signin endpoint no longer 500s (a wrong password should now return
"invalid credentials" instead of the validation crash):

```sh
kubectl exec -n openwebui open-webui-0 -- sh -c \
  'curl -s -o /tmp/resp.txt -w "HTTP %{http_code}\n" \
     -X POST http://localhost:8080/api/v1/auths/signin \
     -H "Content-Type: application/json" \
     --data-binary @- <<EOF && cat /tmp/resp.txt
{"email":"nainjoueur64@gmail.com","password":"wrong-pass-check"}
EOF'
```

```text
HTTP 400
{"detail":"The email or password provided is incorrect. Please check for typos and try logging in again."}
```

## Final outcome

The corrupted `settings` cell was rewritten as a proper JSON object. The user
row now validates through `UserModel`, and the signin endpoint returns normal
"invalid credentials" responses for wrong passwords, meaning real logins work
again. Logging in with the correct password in the browser now succeeds.

The database backup `webui.db.bak-2026-08-11` remains in the PVC at
`/app/backend/data` inside the container as a safety net.

No Kubernetes manifests, Helm values, or storage configuration were changed.
Storage remains on the shared `nfs-k8s` PVC (`open-webui`, 50Gi). No
`local-path` usage was introduced.

## Follow-up

The double-encoding is a data-level bug in upstream Open WebUI
(open-webui/open-webui#26403). If a future version ships a repair migration or
this row regresses, check the upstream issue first. The fix here applies to the
single affected user; a multi-user migration crash would need the patched
migration approach described in the upstream issue.
