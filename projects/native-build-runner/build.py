from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"


def clean() -> None:
    shutil.rmtree(DIST, ignore_errors=True)
    print("clean")


def build() -> None:
    DIST.mkdir(exist_ok=True)
    manifest = {
        "name": "native-build-runner",
        "artifact": "dist/manifest.json",
        "lesson": "targets should be explicit and repeatable",
    }
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("build")


def test() -> None:
    manifest = json.loads((DIST / "manifest.json").read_text())
    assert manifest["name"] == "native-build-runner"
    assert "repeatable" in manifest["lesson"]
    print("test")


def all_targets() -> None:
    clean()
    build()
    test()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("target", choices=["clean", "build", "test", "all"])
    args = parser.parse_args()
    {"clean": clean, "build": build, "test": test, "all": all_targets}[args.target]()


if __name__ == "__main__":
    main()

