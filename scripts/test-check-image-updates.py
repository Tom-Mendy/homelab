#!/usr/bin/env python3
"""Tests for check-image-updates.py without registry access."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("check-image-updates.py")
SPEC = importlib.util.spec_from_file_location("check_image_updates", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class FakeCrane:
    def tags(self, repository: str) -> list[str]:
        return ["1.2.3", "1.3.0", "2.0.0"]

    def digest(self, reference: str) -> str:
        return "sha256:" + "1" * 64


class ImageUpdateTests(unittest.TestCase):
    def test_separate_repository_tag_and_digest_are_one_pinned_image(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = root / "kubernetes/portfolio/values.yaml"
            values.parent.mkdir(parents=True)
            values.write_text(
                "image:\n"
                "  repository: harbor.example.com/portfolio/portfolio "
                '# {"$imagepolicy": "flux-system:portfolio:name"}\n'
                "  tag: latest "
                '# {"$imagepolicy": "flux-system:portfolio:tag"}\n'
                "  digest: sha256:" + "0" * 64 + " "
                '# {"$imagepolicy": "flux-system:portfolio:digest"}\n',
                encoding="utf-8",
            )

            uses = MODULE.collect_images(root / "kubernetes", base_dir=root)

            self.assertEqual(len(uses), 1)
            self.assertEqual(
                uses[0].reference.full_reference,
                "harbor.example.com/portfolio/portfolio:latest@sha256:"
                + "0" * 64,
            )
            self.assertEqual(uses[0].value_kind, "digest")
            self.assertEqual(uses[0].source_key, "image.digest")

    def test_repository_override_config_contains_newt_mapping(self) -> None:
        overrides = MODULE.load_overrides(
            SCRIPT.with_name("image-update-overrides.json")
        )

        self.assertIn(
            MODULE.RepositoryOverride(
                "kubernetes/newt/values.yaml",
                "global.image.tag",
                "docker.io/fosrl/newt",
            ),
            overrides,
        )

    def test_newt_external_repository_override(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            values = root / "kubernetes/newt/values.yaml"
            values.parent.mkdir(parents=True)
            values.write_text(
                "global:\n  image:\n    tag: 1.2.3@sha256:" + "0" * 64 + "\n",
                encoding="utf-8",
            )
            override = MODULE.RepositoryOverride(
                "kubernetes/newt/values.yaml",
                "global.image.tag",
                "docker.io/fosrl/newt",
            )

            uses = MODULE.collect_images(root / "kubernetes", [override], root)

            self.assertEqual(len(uses), 1)
            self.assertEqual(
                uses[0].reference.repository,
                "docker.io/fosrl/newt",
            )
            self.assertEqual(uses[0].source_key, "global.image.tag")
            self.assertEqual(uses[0].value_kind, "tag")

    def test_newer_compatible_tag_has_copyable_tag_value(self) -> None:
        use = MODULE.ImageUse(
            MODULE.ImageReference("example/app", "1.2.3", "sha256:" + "0" * 64),
            [MODULE.Location("values.yaml", 4)],
            "tag",
            "image.tag",
        )

        result = MODULE.check_image(use, FakeCrane(), allow_major=False)

        self.assertEqual(result["status"], "outdated")
        self.assertEqual(result["replacement"], "1.3.0@sha256:" + "1" * 64)
        self.assertEqual(result["latest"], "example/app:1.3.0@sha256:" + "1" * 64)

    def test_major_upgrade_requires_explicit_flag(self) -> None:
        self.assertEqual(
            MODULE.choose_tag("1.2.3", ["1.3.0", "2.0.0"], False),
            "1.3.0",
        )
        self.assertEqual(
            MODULE.choose_tag("1.2.3", ["1.3.0", "2.0.0"], True),
            "2.0.0",
        )


if __name__ == "__main__":
    unittest.main()
