#!/usr/bin/env python3
"""Report newer container image tags and digests used by the homelab charts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


IMAGE_VALUE_RE = re.compile(
    r"\bimage:\s*[\"']?(?P<image>(?!\{\{)[^\s\"']+)[\"']?"
)
REPOSITORY_RE = re.compile(
    r"^\s*repository:\s*[\"']?(?P<repository>[^\s\"']+)[\"']?\s*$"
)
TAG_RE = re.compile(r"^\s*tag:\s*[\"']?(?P<tag>[^\s\"']*)[\"']?\s*$")
DIGEST_RE = re.compile(
    r"^\s*digest:\s*[\"']?(?P<digest>sha256:[a-f0-9]{64})[\"']?\s*$",
    re.IGNORECASE,
)
IMAGE_RE = re.compile(
    r"^(?P<repository>(?:[a-z0-9.-]+(?::[0-9]+)?/)?[a-z0-9._-]+(?:/[a-z0-9._-]+)*?)"
    r"(?::(?P<tag>[^@]+))?(?:@(?P<digest>sha256:[a-f0-9]{64}))?$",
    re.IGNORECASE,
)
SEMVER_RE = re.compile(
    r"^(?P<prefix>v?)(?P<major>\d+)"
    r"(?:\.(?P<minor>\d+))?(?:\.(?P<patch>\d+))?"
    r"(?P<suffix>[-_].*)?$"
)


@dataclass(frozen=True)
class Location:
    path: str
    line: int


@dataclass(frozen=True)
class ImageReference:
    repository: str
    tag: str
    digest: str | None

    @property
    def tag_reference(self) -> str:
        return f"{self.repository}:{self.tag}"

    @property
    def full_reference(self) -> str:
        if self.digest:
            return f"{self.tag_reference}@{self.digest}"
        return self.tag_reference


@dataclass
class ImageUse:
    reference: ImageReference
    locations: list[Location]


def parse_reference(value: str) -> ImageReference | None:
    """Parse a Docker reference and treat an omitted tag as latest."""

    value = value.strip().strip("'\"").rstrip(",")
    if not value or value.startswith(("{{", "http://", "https://")):
        return None

    match = IMAGE_RE.fullmatch(value)
    if not match:
        return None

    repository = match.group("repository")
    tag = match.group("tag") or "latest"
    digest = match.group("digest")
    if "{{" in repository or "{{" in tag:
        return None
    return ImageReference(repository, tag, digest)


def iter_yaml_files(root: Path) -> list[Path]:
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix in {".yaml", ".yml"}
    )


def collect_images(root: Path) -> list[ImageUse]:
    found: dict[str, ImageUse] = {}

    def add(value: str, path: Path, line_number: int) -> None:
        reference = parse_reference(value)
        if reference is None:
            return
        key = reference.full_reference
        use = found.setdefault(key, ImageUse(reference, []))
        location = Location(str(path), line_number)
        if location not in use.locations:
            use.locations.append(location)

    for path in iter_yaml_files(root):
        lines = path.read_text(encoding="utf-8").splitlines()
        pending_repository: tuple[str, int, int] | None = None

        for index, line in enumerate(lines, start=1):
            image_match = IMAGE_VALUE_RE.search(line)
            if image_match:
                add(image_match.group("image"), path, index)

            repository_match = REPOSITORY_RE.match(line)
            if repository_match:
                pending_repository = (
                    repository_match.group("repository"),
                    len(line) - len(line.lstrip()),
                    index,
                )
                continue

            tag_match = TAG_RE.match(line)
            if tag_match and pending_repository is not None:
                repository, repository_indent, repository_line = pending_repository
                tag_indent = len(line) - len(line.lstrip())
                if tag_indent == repository_indent:
                    tag = tag_match.group("tag")
                    if tag:
                        add(f"{repository}:{tag}", path, repository_line)
                        pending_repository = None
                    continue

            digest_match = DIGEST_RE.match(line)
            if digest_match and pending_repository is not None:
                repository, repository_indent, repository_line = pending_repository
                digest_indent = len(line) - len(line.lstrip())
                if digest_indent == repository_indent:
                    add(
                        f"{repository}:latest@{digest_match.group('digest')}",
                        path,
                        repository_line,
                    )
                    pending_repository = None
                    continue

            if line.strip() and not line.lstrip().startswith("#"):
                indent = len(line) - len(line.lstrip())
                if pending_repository is not None and indent <= pending_repository[1]:
                    pending_repository = None

    return sorted(found.values(), key=lambda use: use.reference.full_reference)


class Crane:
    def __init__(self, executable: str) -> None:
        self.executable = executable

    def run(self, *arguments: str) -> str:
        result = subprocess.run(
            [self.executable, *arguments],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(message or f"exit status {result.returncode}")
        return result.stdout.strip()

    def tags(self, repository: str) -> list[str]:
        return [tag for tag in self.run("ls", repository).splitlines() if tag]

    def digest(self, reference: str) -> str:
        return self.run("digest", reference)


def semver_parts(tag: str) -> tuple[str, int, int, int, str] | None:
    match = SEMVER_RE.fullmatch(tag)
    if not match:
        return None
    return (
        match.group("prefix"),
        int(match.group("major")),
        int(match.group("minor") or 0),
        int(match.group("patch") or 0),
        match.group("suffix") or "",
    )


def choose_tag(current_tag: str, tags: list[str], allow_major: bool) -> str:
    current = semver_parts(current_tag)
    if current is None:
        return current_tag

    prefix, major, _, _, suffix = current
    candidates: list[tuple[tuple[int, int, int], str]] = []
    for tag in tags:
        parsed = semver_parts(tag)
        if parsed is None or parsed[0] != prefix or parsed[4] != suffix:
            continue
        if not allow_major and parsed[1] != major:
            continue
        candidates.append(((parsed[1], parsed[2], parsed[3]), tag))

    if not candidates:
        return current_tag
    return max(candidates)[1]


def check_image(use: ImageUse, crane: Crane, allow_major: bool) -> dict[str, object]:
    reference = use.reference
    tags = crane.tags(reference.repository)
    selected_tag = choose_tag(reference.tag, tags, allow_major)
    selected_reference = f"{reference.repository}:{selected_tag}"
    selected_digest = crane.digest(selected_reference)
    current_digest = reference.digest

    if current_digest is None:
        status = "outdated"
        reason = "image is not pinned by digest"
    elif selected_digest != current_digest or selected_tag != reference.tag:
        status = "outdated"
        reason = "newer compatible tag or digest is available"
    else:
        status = "current"
        reason = "tag and digest match the registry"

    return {
        "status": status,
        "reason": reason,
        "current": reference.full_reference,
        "latest": f"{selected_reference}@{selected_digest}",
        "locations": [f"{location.path}:{location.line}" for location in use.locations],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Report image updates without editing Kubernetes manifests."
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("kubernetes"),
        help="Directory to scan (default: kubernetes).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show images that are already current as well as outdated images.",
    )
    parser.add_argument(
        "--allow-major",
        action="store_true",
        help="Consider newer major versions for semantic-version tags.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of the human report.",
    )
    parser.add_argument(
        "--crane",
        default=shutil.which("crane") or "/tmp/crane",
        help="Path to the crane executable (default: crane or /tmp/crane).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.path.is_dir():
        print(f"error: scan path does not exist: {args.path}", file=sys.stderr)
        return 2
    if not Path(args.crane).exists() and shutil.which(args.crane) is None:
        print(
            "error: crane is required; install it or pass --crane /path/to/crane",
            file=sys.stderr,
        )
        return 2

    uses = collect_images(args.path)
    if not uses:
        print(f"No image references found under {args.path}")
        return 0

    crane = Crane(args.crane)
    results: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    for use in uses:
        try:
            results.append(check_image(use, crane, args.allow_major))
        except RuntimeError as error:
            errors.append(
                {
                    "status": "error",
                    "current": use.reference.full_reference,
                    "error": str(error),
                    "locations": [
                        f"{location.path}:{location.line}" for location in use.locations
                    ],
                }
            )

    if args.json:
        print(json.dumps({"images": results, "errors": errors}, indent=2))
    else:
        for result in results:
            if result["status"] == "current" and not args.all:
                continue
            print(f"[{result['status']}] {result['current']}")
            print(f"  latest: {result['latest']}")
            print(f"  reason: {result['reason']}")
            print(f"  used at: {', '.join(result['locations'])}")
        for error in errors:
            print(f"[error] {error['current']}: {error['error']}", file=sys.stderr)
            print(f"  used at: {', '.join(error['locations'])}", file=sys.stderr)

    if errors:
        return 2
    return 1 if any(result["status"] == "outdated" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
