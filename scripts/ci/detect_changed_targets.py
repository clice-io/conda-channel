#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from pathlib import Path


def write_output(key: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if not output_file:
        print("GITHUB_OUTPUT is not set", file=sys.stderr)
        sys.exit(1)
    with open(output_file, "a", encoding="utf-8") as handle:
        handle.write(f"{key}={value}\n")


def list_targets(recipe_root: Path) -> list[str]:
    return sorted([p.name for p in recipe_root.iterdir() if p.is_dir()])


def targets_from_git_diff(recipe_root: str, before_sha: str, head_sha: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", before_sha, head_sha, "--", recipe_root]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    targets = set()
    for line in result.stdout.splitlines():
        parts = line.strip().split("/")
        if len(parts) >= 2:
            targets.add(parts[1])
    return sorted(targets)


def main() -> int:
    recipe_root = os.environ.get("RECIPE_ROOT", "recipe")
    event_name = os.environ.get("EVENT_NAME", "")
    before_sha = os.environ.get("BEFORE_SHA", "")
    head_sha = os.environ.get("HEAD_SHA", os.environ.get("GITHUB_SHA", ""))

    recipe_path = Path(recipe_root)
    if not recipe_path.is_dir():
        write_output("matrix", json.dumps({"include": []}))
        write_output("has_changes", "false")
        return 0

    if event_name == "workflow_dispatch":
        targets = list_targets(recipe_path)
    elif not before_sha or before_sha == "0000000000000000000000000000000000000000":
        targets = list_targets(recipe_path)
    else:
        targets = targets_from_git_diff(recipe_root, before_sha, head_sha)

    if not targets:
        write_output("matrix", json.dumps({"include": []}))
        write_output("has_changes", "false")
        return 0

    platforms = [
        ("linux-64", "ubuntu-latest"),
        ("osx-arm64", "macos-latest"),
        ("win-64", "windows-latest"),
    ]

    entries: list[dict[str, str]] = []
    for target in targets:
        recipe_file = recipe_path / target / "recipe.yaml"
        if not recipe_file.exists():
            recipe_file = recipe_path / target / "meta.yaml"
        if not recipe_file.exists():
            print(f"Warning: Recipe file not found for {target}, skipping.")
            continue

        for target_platform, os_name in platforms:
            entries.append(
                {
                    "target": target,
                    "recipe": str(recipe_file),
                    "target_platform": target_platform,
                    "os": os_name,
                }
            )

    if not entries:
        write_output("matrix", json.dumps({"include": []}))
        write_output("has_changes", "false")
        return 0

    write_output("matrix", json.dumps({"include": entries}))
    write_output("has_changes", "true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
