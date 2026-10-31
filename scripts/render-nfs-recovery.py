#!/usr/bin/env python3
"""Render a gated, temporary maintenance controller; never copy credentials."""
import json
import pathlib

SCRIPT = pathlib.Path(__file__).with_name("recover-nfs-worker.py")
NAMESPACE = "nfs-maintenance"
NAME = "nfs-worker-recovery"
IMAGE = "docker.io/library/python@sha256:8acac70227ce3b34da9453120c375cc5b66cd0b062d4dc6bc74286f81a3819e1"


def manifests():
    metadata = {"name": NAME, "namespace": NAMESPACE}
    return [
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": NAMESPACE, "labels": {
            "pod-security.kubernetes.io/enforce": "privileged", "app.kubernetes.io/part-of": NAME}}},
        {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": metadata},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": {"name": NAME}, "rules": [
            {"apiGroups": [""], "resources": ["nodes"], "resourceNames": ["node2", "node3"], "verbs": ["get", "patch"]},
            {"apiGroups": [""], "resources": ["pods"], "verbs": ["get", "list", "delete"]},
            {"apiGroups": ["apps"], "resources": ["deployments", "statefulsets"], "verbs": ["get", "list"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding", "metadata": {"name": NAME},
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": NAME},
            "subjects": [{"kind": "ServiceAccount", "name": NAME, "namespace": NAMESPACE}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role", "metadata": metadata, "rules": [
            {"apiGroups": [""], "resources": ["configmaps"], "resourceNames": [NAME], "verbs": ["get", "patch"]},
            {"apiGroups": [""], "resources": ["pods"], "verbs": ["create"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding", "metadata": metadata,
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": NAME},
            "subjects": [{"kind": "ServiceAccount", "name": NAME, "namespace": NAMESPACE}]},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": metadata, "data": {"execute": "false", "stage": "WaitingForPreparation"}},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": NAME + "-script", "namespace": NAMESPACE},
            "data": {"recover.py": SCRIPT.read_text()}},
        {"apiVersion": "batch/v1", "kind": "Job", "metadata": metadata, "spec": {
            "backoffLimit": 0, "activeDeadlineSeconds": 7200, "ttlSecondsAfterFinished": 86400,
            "template": {"metadata": {"labels": {"app.kubernetes.io/name": NAME}}, "spec": {
                "serviceAccountName": NAME, "nodeSelector": {"kubernetes.io/hostname": "node2"},
                "restartPolicy": "Never", "securityContext": {"runAsNonRoot": True, "runAsUser": 10000,
                    "runAsGroup": 10000, "seccompProfile": {"type": "RuntimeDefault"}},
                "containers": [{"name": "controller", "image": IMAGE, "imagePullPolicy": "IfNotPresent",
                    "command": ["python3", "-u", "/script/recover.py"],
                    "env": [{"name": "RECOVERY_WORKER", "value": "node3"},
                            {"name": "CONTROLLER_NODE", "valueFrom": {"fieldRef": {"fieldPath": "spec.nodeName"}}}],
                    "resources": {"requests": {"cpu": "25m", "memory": "64Mi"}, "limits": {"memory": "192Mi"}},
                    "securityContext": {"allowPrivilegeEscalation": False, "readOnlyRootFilesystem": True,
                        "capabilities": {"drop": ["ALL"]}},
                    "volumeMounts": [{"name": "script", "mountPath": "/script", "readOnly": True}]}],
                "volumes": [{"name": "script", "configMap": {"name": NAME + "-script"}}]}}}}
    ]


if __name__ == "__main__":
    print(json.dumps({"apiVersion": "v1", "kind": "List", "items": manifests()}))
