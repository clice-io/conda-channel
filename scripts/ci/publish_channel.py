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
        packages = find_packages(artifacts_dir)
        if not packages:
            print(f"No packages found under {artifacts_dir}", file=sys.stderr)
            return 1
        copy_tree(artifacts_dir, channel_dir)
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
