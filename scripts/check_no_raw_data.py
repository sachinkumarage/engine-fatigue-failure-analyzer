"""Fail if any file under data/ is tracked by git."""

import subprocess
import sys
from collections.abc import Iterable

PROTECTED_PREFIX = "data/"


def find_protected_paths(paths: Iterable[str]) -> list[str]:
    """Return the paths that lie under the protected data/ folder."""
    return [
        p
        for p in paths
        if p.replace("\\", "/").removeprefix("./").startswith(PROTECTED_PREFIX)
    ]


def tracked_files() -> list[str]:
    """Return the list of files tracked by git."""
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    )
    return [line for line in result.stdout.splitlines() if line]


def main() -> int:
    offending = find_protected_paths(tracked_files())
    if offending:
        print("Tracked files under data/ are not allowed:")
        for path in offending:
            print(f"  {path}")
        return 1
    print("OK: no tracked files under data/.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
