"""sample.py - generate sample sources + a build manifest so the engine runs
out of the box.

This writes:
  src/greeting.txt, src/name.txt   -> source inputs
  build.json                       -> the manifest describing the target DAG

The sample DAG models a classic compile/link shape:

    name_obj   (concat src/name.txt)        \
                                              >-- app  (count_lines, links both)
    greeting_obj (concat src/greeting.txt)  /

    report     (count_lines over app + an extra input)

Run this once, then `python3 mini_build.py build all` twice to see cache hits,
touch a source to see an incremental rebuild.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"


SAMPLE_SOURCES = {
    "src/greeting.txt": "hello\nworld\n",
    "src/name.txt": "mini-build-graph\n",
    "src/notes.txt": "this file is a declared input of the report target\n",
}


MANIFEST = {
    "targets": [
        {
            "name": "name_obj",
            "inputs": ["src/name.txt"],
            "action": "concat",
            "output": "out/name.obj",
        },
        {
            "name": "greeting_obj",
            "inputs": ["src/greeting.txt"],
            "action": "concat",
            "output": "out/greeting.obj",
        },
        {
            "name": "app",
            "deps": ["name_obj", "greeting_obj"],
            "action": "count_lines",
            "output": "out/app.txt",
        },
        {
            "name": "report",
            "inputs": ["src/notes.txt"],
            "deps": ["app"],
            "action": "count_lines",
            "output": "out/report.txt",
        },
    ]
}


def generate() -> None:
    SRC.mkdir(parents=True, exist_ok=True)
    for rel, content in SAMPLE_SOURCES.items():
        path = ROOT / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    (ROOT / "build.json").write_text(json.dumps(MANIFEST, indent=2) + "\n")
    print(f"wrote {len(SAMPLE_SOURCES)} source files and build.json under {ROOT}")


if __name__ == "__main__":
    generate()
