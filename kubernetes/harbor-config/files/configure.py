import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ["HARBOR_URL"].rstrip("/")
AUTH = ("admin", os.environ["HARBOR_ADMIN_PASSWORD"])


def request(method, path, payload=None, expected=(200, 201, 204, 404)):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    token = base64.b64encode(f"{AUTH[0]}:{AUTH[1]}".encode()).decode()
    req.add_header("Authorization", f"Basic {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            if response.status not in expected:
                raise RuntimeError(f"Harbor API {method} {path}: HTTP {response.status}")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        if exc.code not in expected:
            detail = exc.read().decode(errors="replace")[:500]
            raise RuntimeError(f"Harbor API {method} {path}: HTTP {exc.code}: {detail}") from exc
        return exc.code, None


def wait_for_harbor():
    for _ in range(60):
        try:
            status, _ = request("GET", "/api/v2.0/health", expected=(200,))
            if status == 200:
                return
        except Exception:
            time.sleep(5)
    raise RuntimeError("Harbor did not become ready within five minutes")


def registry_by_name(name):
    _, registries = request("GET", "/api/v2.0/registries?page_size=100", expected=(200,))
    return next((item for item in registries if item["name"] == name), None)


def project_by_name(name):
    encoded = urllib.parse.quote(name, safe="")
    status, project = request("GET", f"/api/v2.0/projects/{encoded}", expected=(200, 404))
    return project if status == 200 else None


def credentials(username_key, password_key):
    if not username_key or not password_key:
        return None
    username = os.environ.get(username_key, "")
    password = os.environ.get(password_key, "")
    if not username or not password:
        return None
    return {"type": "basic", "access_key": username, "access_secret": password}


def configure_registry(project):
    name = project["registryName"]
    existing = registry_by_name(name)
    payload = {
        "name": name,
        "description": f"Managed proxy source for {project['name']}",
        "type": project["registryType"],
        "url": project["registryUrl"],
        "insecure": False,
    }
    credential = credentials(project.get("usernameKey"), project.get("passwordKey"))
    if credential:
        payload["credential"] = credential
    if existing is None:
        request("POST", "/api/v2.0/registries", payload, expected=(201,))
        existing = registry_by_name(name)
    if not existing:
        raise RuntimeError(f"Registry endpoint {name} was not created")
    elif existing["type"] != project["registryType"] or existing["url"] != project["registryUrl"]:
        encoded_id = urllib.parse.quote(str(existing["id"]), safe="")
        request("PUT", f"/api/v2.0/registries/{encoded_id}", payload, expected=(200,))
    return existing["id"]


def configure_project(project, registry_id):
    name = project["name"]
    prevent_vulnerable = project.get("preventVulnerabilities", True)
    payload = {
        "project_name": name,
        "metadata": {
            "public": "true" if project.get("public", True) else "false",
            "auto_scan": "true",
            "auto_sbom_generation": "true",
            "prevent_vul": "true" if prevent_vulnerable else "false",
            "severity": "high",
            "reuse_sys_cve_allowlist": "true",
        },
        "storage_limit": project["storageLimit"],
    }
    if registry_id is not None:
        payload["registry_id"] = registry_id
    existing = project_by_name(name)
    if existing is None:
        request("POST", "/api/v2.0/projects", payload, expected=(201, 409))
    else:
        encoded = urllib.parse.quote(name, safe="")
        request("PUT", f"/api/v2.0/projects/{encoded}", payload, expected=(200,))


wait_for_harbor()
projects = json.loads(os.environ["HARBOR_PROXY_PROJECTS"])
for project in projects:
    registry_id = None if project.get("projectType") == "local" else configure_registry(project)
    configure_project(project, registry_id)
print(f"Configured {len(projects)} Harbor projects")
