from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def main() -> None:
    nix = shutil.which("nix")
    if nix is None:
        print("nix not installed; install Nix, then run `nix develop` in this directory")
        return
    subprocess.run([nix, "flake", "show"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()

