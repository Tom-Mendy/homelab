"""Scheduling-accounting cases that could hide a maintenance capacity failure."""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "node2_capacity", Path(__file__).parents[1] / "check-node2-capacity.py")
CAPACITY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CAPACITY)


def container(memory, restart=False):
    result = {"resources": {"requests": {"memory": memory}}}
    if restart:
        result["restartPolicy"] = "Always"
    return result


class CapacityTests(unittest.TestCase):
    def test_serial_init_is_not_added_to_steady_state(self):
        pod = {"containers": [container("1Gi"), container("512Mi")],
               "initContainers": [container("2Gi"), container("1Gi")]}
        self.assertEqual(CAPACITY.requests(pod)["memory"], 2 * CAPACITY.GIB)

    def test_sidecar_and_later_init_overlap(self):
        pod = {"containers": [container("1Gi")],
               "initContainers": [container("512Mi", True), container("2Gi")],
               "overhead": {"memory": "64Mi"}}
        self.assertEqual(CAPACITY.requests(pod)["memory"], 2624 * CAPACITY.MIB)

    def test_sidecar_does_not_overlap_an_earlier_init(self):
        pod = {"containers": [container("1Gi")],
               "initContainers": [container("2Gi"), container("512Mi", True)]}
        self.assertEqual(CAPACITY.requests(pod)["memory"], 2 * CAPACITY.GIB)

    def test_pod_request_overrides_container_aggregate(self):
        pod = {"containers": [container("1Gi")],
               "resources": {"requests": {"memory": "3Gi"}}}
        self.assertEqual(CAPACITY.requests(pod)["memory"], 3 * CAPACITY.GIB)

    def test_required_node_affinity_is_enforced(self):
        pod = {"spec": {"affinity": {"nodeAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": {
                "nodeSelectorTerms": [{"matchFields": [{"key": "metadata.name",
                    "operator": "In", "values": ["node2"]}]}]}}}}}
        node = {"metadata": {"name": "node3", "labels": {}}, "spec": {}}
        self.assertIn("required node affinity", CAPACITY.placement(pod, node))

    def test_hard_pod_affinity_requires_review(self):
        pod = {"spec": {"affinity": {"podAntiAffinity": {
            "requiredDuringSchedulingIgnoredDuringExecution": [{"topologyKey": "zone"}]}}}}
        node = {"metadata": {"name": "node3", "labels": {}}, "spec": {}}
        self.assertTrue(CAPACITY.placement(pod, node))


if __name__ == "__main__":
    unittest.main()
