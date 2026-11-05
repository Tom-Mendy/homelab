"""One-shot Helm pre-upgrade gate for the self-hosted GitOps repository."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import ssl
import subprocess
import tarfile
import time
import urllib.error
import urllib.request

os.umask(0o077)
sa = Path('/var/run/secrets/kubernetes.io/serviceaccount')
context = ssl.create_default_context(cafile=str(sa / 'ca.crt'))
token = (sa / 'token').read_text().strip()
base = 'https://kubernetes.default.svc'
namespace = 'forgejo'
endpoint = f'/apis/apps/v1/namespaces/{namespace}/deployments'

def api(method, path, body=None):
    request = urllib.request.Request(
        base + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(request, context=context, timeout=25) as response:
        return json.load(response)

def restore_object(deployment):
    metadata = deployment['metadata']
    for key in ('uid', 'resourceVersion', 'generation', 'creationTimestamp', 'managedFields'):
        metadata.pop(key, None)
    deployment.pop('status', None)
    return deployment

def main():
    for variable in ('PGHOST', 'PGUSER', 'PGPASSWORD', 'PGDATABASE'):
        if not os.environ.get(variable):
            raise RuntimeError('Required database configuration is missing')
    backup = Path(os.environ.get('BACKUP_ROOT', '/backups')) / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup.mkdir(mode=0o700)
    previous = api('GET', endpoint + '/forgejo')
    (backup / 'previous-deployment.json').write_text(json.dumps(previous))
    removed = False
    try:
        api('DELETE', endpoint + '/forgejo', {
            'propagationPolicy': 'Foreground',
            'preconditions': {'uid': previous['metadata']['uid']},
        })
        removed = True
        for _ in range(90):
            pods = api('GET', f'/api/v1/namespaces/{namespace}/pods?labelSelector=app%3Dforgejo')
            if not pods['items']:
                break
            time.sleep(2)
        else:
            raise RuntimeError('Old Forgejo pods did not terminate')
        dump = backup / 'forgejo.dump'
        subprocess.run(['pg_dump', '-Fc', '--no-owner', '-f', str(dump)], check=True, timeout=180)
        listing = subprocess.run(['pg_restore', '--list', str(dump)], capture_output=True, check=True, timeout=45)
        if b'TABLE' not in listing.stdout or dump.read_bytes()[:5] != b'PGDMP':
            raise RuntimeError('Invalid database archive')
        archive = backup / 'data.tar.gz'
        def application_files(member):
            parts = Path(member.name).parts
            # Synology trash and generated thumbnail indexes are not Forgejo data.
            if '@eaDir' in parts or member.name == 'data/#recycle' or member.name.startswith('data/#recycle/'):
                return None
            return member
        with tarfile.open(archive, 'w:gz') as tar:
            tar.add('/data', arcname='data', filter=application_files)
        with tarfile.open(archive, 'r:gz') as tar:
            members = tar.getmembers()
            if not members:
                raise RuntimeError('Empty data archive')
            # Read every archived regular file to exercise the gzip CRC completely.
            for member in members:
                if member.isfile():
                    stream = tar.extractfile(member)
                    assert stream is not None
                    while stream.read(1024 * 1024):
                        pass
        manifest = {'state': 'complete', 'database_archive': dump.name,
                    'filesystem_archive': archive.name, 'filesystem_members': len(members),
                    'database_bytes': dump.stat().st_size, 'filesystem_bytes': archive.stat().st_size}
        (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2))
        print(json.dumps(manifest), flush=True)
    except BaseException:
        if removed:
            try:
                api('POST', endpoint, restore_object(previous))
                print('Backup failed; previous Deployment recreated', flush=True)
            except Exception:
                print('Backup failed; operator must restore previous-deployment.json', flush=True)
        raise

if __name__ == '__main__':
    def interrupted(signum, frame):
        raise RuntimeError('Maintenance interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    main()
