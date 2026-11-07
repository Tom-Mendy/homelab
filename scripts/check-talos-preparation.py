# /// script
# requires-python = ">=3.11"
# dependencies = ["PyYAML==6.0.3"]
# ///
"""Read-only verification of Talos candidates and the separate network allocation."""

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import subprocess

import yaml


def check(condition, message):
    if not condition:
        raise ValueError(message)


def address_range(bounds):
    start, end = map(ipaddress.ip_address, bounds)
    check(start <= end, "Address range is reversed")
    return {ipaddress.ip_address(n) for n in range(int(start), int(end) + 1)}


def verify(plan, candidates, tool, context):
    net = plan["network"]
    ubuntu = address_range(net["ubuntu_metallb"])
    talos = address_range(net["talos_metallb"])
    vip = ipaddress.ip_address(net["talos_api_vip"])
    lan = ipaddress.ip_network(net["lan"])
    check(not ubuntu & talos and vip not in ubuntu | talos,
          "VIP and load-balancer pools overlap")
    check(all(ip in lan for ip in ubuntu | talos | {vip}), "Allocation outside LAN")
    cidrs = [ipaddress.ip_network(net[key]) for key in
             ["lan", "pod_cidr", "service_cidr", "ubuntu_pod_cidr", "ubuntu_service_cidr"]]
    check(all(not a.overlaps(b) for i, a in enumerate(cidrs) for b in cidrs[i+1:]),
          "Cluster or LAN CIDRs overlap")
    digest = hashlib.file_digest(tool.open("rb"), "sha256").hexdigest()
    check(digest == plan["tools"]["talosctl"]["sha256"], "Unexpected talosctl binary")
    endpoint = "https://" + net["talos_api_hostname"] + ":6443"
    results = []
    for node in plan["nodes"]:
        path = candidates / ("controlplane-" + node["node"] + "-candidate.yaml")
        docs = list(yaml.safe_load_all(path.read_text()))

        def document(kind):
            selected = [d for d in docs if d.get("kind") == kind]
            check(len(selected) == 1, "Missing or duplicate configuration document")
            return selected[0]

        check(document("KubeClusterConfig")["endpoint"] == endpoint, "Wrong API endpoint")
        install = document("UnattendedInstallConfig")
        check(install["installer"]["image"] == plan["installer"]["image"], "Wrong installer")
        check(not install["provisioning"].get("wipe", False), "Unexpected disk wipe setting")
        check("REPLACE_ME_AFTER_TALOS_ISO_DISK_CHECK" in
              install["provisioning"]["diskSelector"]["match"],
              "Disk selector changed; require a separate ISO inspection review")
        check(document("Layer2VIPConfig")["name"] == str(vip), "Wrong VIP")
        check(document("Layer2VIPConfig")["link"] == "lan0", "Wrong VIP link")
        alias = document("LinkAliasConfig")
        check(alias["name"] == "lan0" and alias["selector"]["match"] ==
              'mac(link.permanent_addr) == "' + node["mac"] + '"', "Wrong NIC selector")
        link = document("LinkConfig")
        check(link["name"] == "lan0" and
              link["addresses"] == [{"address": node["ip"] + "/24"}], "Wrong node address")
        check(link["routes"] == [{"gateway": net["gateway"]}], "Wrong gateway")
        check(document("HostnameConfig")["hostname"] == node["node"], "Wrong hostname")
        kube_node = document("KubeNodeConfig")
        check(not kube_node.get("taints"), "Talos control plane rejects application workloads")
        check("node.kubernetes.io/exclude-from-external-load-balancers" not in
              kube_node.get("labels", {}), "MetalLB cannot announce from the control plane")
        check(kube_node["nodeIP"]["validSubnets"] == [node["ip"] + "/32"],
              "Kubelet may choose the VIP as its node IP")
        network = document("KubeNetworkConfig")
        check(network["podSubnets"] == [net["pod_cidr"]] and
              network["serviceSubnets"] == [net["service_cidr"]], "Wrong cluster CIDRs")
        api = document("KubeAPIServerConfig")
        check(set(api["certExtraSANs"]) == {net["talos_api_hostname"], str(vip)},
              "API certificate SANs include an unexpected endpoint")
        for kind in ["KubeletConfig", "KubeAPIServerConfig", "KubeControllerManagerConfig",
                     "KubeSchedulerConfig", "KubeProxyConfig"]:
            check(document(kind)["image"].endswith(":" + plan["kubernetes_version"]),
                  "Kubernetes component versions differ")
        validation = subprocess.run([str(tool), "validate", "--config", str(path),
                                     "--strict", "--mode", "metal"], capture_output=True)
        (candidates / (node["node"] + "-validation.log")).write_bytes(
            validation.stdout + validation.stderr)
        check(validation.returncode == 0, "Candidate schema validation failed")
        results.append({"node": node["node"], "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "schema_valid": True, "disk_confirmed": False})

    base = ["kubectl", "--context", context, "--request-timeout=30s"]

    def get(resource):
        return json.loads(subprocess.run(base + ["get", resource, "-A", "-o", "json"],
                                         check=True, capture_output=True).stdout)["items"]

    pools = get("ipaddresspools.metallb.io")
    check(len(pools) == 1 and pools[0]["spec"]["addresses"] ==
          ["-".join(net["ubuntu_metallb"])], "Ubuntu live pool differs from the reservation")
    for service in get("services"):
        for entry in service.get("status", {}).get("loadBalancer", {}).get("ingress", []):
            if entry.get("ip"):
                check(ipaddress.ip_address(entry["ip"]) in ubuntu,
                      "An Ubuntu service occupies an address outside its pool")
    answers = {}
    for server in ["1.1.1.1", "10.0.0.61"]:
        response = subprocess.run(["dig", "@" + server, net["talos_api_hostname"],
                                   "A", "+short", "+time=3", "+tries=1"],
                                  check=True, capture_output=True, text=True)
        check(response.stdout.splitlines() == [str(vip)], "DNS does not target only the VIP")
        answers[server] = [str(vip)]
    return {"prepared": True, "installation_approved": False,
            "talos_version": plan["talos_version"], "kubernetes_version": plan["kubernetes_version"],
            "endpoint": endpoint, "dns_answers": answers, "candidates": results,
            "live_talos_api_tested": False, "talos_metallb_applied": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("talos/migration-plan.json"))
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--talosctl", type=Path, required=True)
    parser.add_argument("--ubuntu-context", default="kubernetes-admin@cluster.local")
    args = parser.parse_args()
    try:
        result = verify(json.loads(args.plan.read_text()), args.candidates, args.talosctl,
                        args.ubuntu_context)
    except (OSError, ValueError, KeyError, yaml.YAMLError, subprocess.CalledProcessError):
        parser.exit(1, "Talos preparation check failed; inspect private evidence.\n")
    (args.candidates / "preparation-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
