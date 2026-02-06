#!/usr/bin/env python3
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path


def copy_tree(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def find_packages(root: Path) -> list[Path]:
    packages = list(root.rglob("*.conda"))
    packages.extend(root.rglob("*.tar.bz2"))
    return packages


KNOWN_PLATFORMS = ["linux-64", "win-64", "osx-arm64", "noarch"]


def platform_from_name(name: str) -> str | None:
    if name in KNOWN_PLATFORMS:
        return name
    for platform in KNOWN_PLATFORMS:
        if name.endswith(f"-{platform}"):
            return platform
    return None


def copy_packages(src: Path, dst: Path) -> None:
    for pkg in find_packages(src):
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pkg, dst / pkg.name)


def main() -> int:
    channel_dir = Path(os.environ.get("CHANNEL_DIR", "channel"))
    artifacts_dir = Path(os.environ.get("ARTIFACTS_DIR", "artifacts"))
    threads = os.environ.get("CONDA_INDEX_THREADS", "4")

    channel_dir.mkdir(parents=True, exist_ok=True)
    git_dir = channel_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    build_artifacts = artifacts_dir / "build_artifacts"
    if build_artifacts.is_dir():
        packages = find_packages(build_artifacts)
        if not packages:
            print(f"No packages found under {build_artifacts}", file=sys.stderr)
            return 1
        copy_tree(build_artifacts, channel_dir)
    elif artifacts_dir.is_dir():
        root_packages = [
            p
            for p in artifacts_dir.iterdir()
            if p.is_file() and (p.name.endswith(".conda") or p.name.endswith(".tar.bz2"))
        ]
        if root_packages:
            print(
                f"Packages were downloaded into {artifacts_dir} without platform subdirs. "
                "Disable merge-multiple or keep platform folders in artifacts.",
                file=sys.stderr,
            )
            return 1

        found = False
        # Case 1: artifacts/<platform>/...
        for subdir in artifacts_dir.iterdir():
            if not subdir.is_dir():
                continue
            platform = platform_from_name(subdir.name)
            if not platform:
                continue
            if find_packages(subdir):
                copy_packages(subdir, channel_dir / platform)
                found = True

        # Case 2: artifacts/<artifact-name>/... where name endswith platform
        if not found:
            for subdir in artifacts_dir.iterdir():
                if not subdir.is_dir():
                    continue
                platform = platform_from_name(subdir.name)
                if not platform:
                    continue
                if find_packages(subdir):
                    copy_packages(subdir, channel_dir / platform)
                    found = True

        # Case 3: artifacts/<folder>/platform/... (e.g. upload/)
        if not found:
            for subdir in artifacts_dir.iterdir():
                if not subdir.is_dir():
                    continue
                for platform_dir in subdir.iterdir():
                    if not platform_dir.is_dir():
                        continue
                    platform = platform_from_name(platform_dir.name)
                    if not platform:
                        continue
                    if find_packages(platform_dir):
                        copy_packages(platform_dir, channel_dir / platform)
                        found = True

        if not found:
            print(f"No packages found under {artifacts_dir}", file=sys.stderr)
            return 1
    else:
        print(f"No artifacts found at {artifacts_dir}", file=sys.stderr)
        return 1

    (channel_dir / "noarch").mkdir(parents=True, exist_ok=True)

    conda_index_cmd = os.environ.get("CONDA_INDEX_CMD", "python -m conda_index")
    subprocess.run(
        shlex.split(conda_index_cmd) + [str(channel_dir), "--threads", threads],
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
