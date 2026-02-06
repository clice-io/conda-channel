#!/usr/bin/env python3
import os
import sys
from pathlib import Path


def main() -> int:
    sccache_dir = os.environ.get("SCCACHE_DIR")
    if not sccache_dir:
        print("SCCACHE_DIR is not set", file=sys.stderr)
        return 1
    Path(sccache_dir).mkdir(parents=True, exist_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
