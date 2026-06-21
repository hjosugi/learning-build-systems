from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    bazel = shutil.which("bazelisk") or shutil.which("bazel")
    if bazel is None:
        print("bazel/bazelisk not installed; install one, then run `bazel test //...` in this directory")
        return
    subprocess.run([bazel, "test", "//..."], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

