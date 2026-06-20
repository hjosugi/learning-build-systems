"""demo.py - run the whole incremental-build story end to end, non-interactively.

This is the fastest way to *see* the four ideas in action. It:
  1. (re)generates the sample sources + manifest
  2. builds from a cold cache    -> everything REBUILT
  3. builds again, no changes    -> everything cache-hit
  4. touches one source          -> only the affected sub-DAG rebuilds
  5. runs --explain on a target  -> prints WHY
  6. demonstrates the hermeticity warning on a deliberately leaky target

It cleans up after itself and leaves the sample manifest in place so you can
poke at the CLI yourself afterwards.
"""

from __future__ import annotations

import json
from pathlib import Path

import mini_build as mb
import sample

ROOT = Path(__file__).resolve().parent


def banner(text: str) -> None:
    print("\n" + "=" * 70)
    print(text)
    print("=" * 70)


def main() -> int:
    # Start from a clean, reproducible slate.
    cache = ROOT / mb.Engine.CACHE_FILE
    cache.unlink(missing_ok=True)
    sample.generate()
    manifest = mb.Manifest.load(ROOT / "build.json")

    banner("1) DEPENDENCY GRAPH (topological order, deps first)")
    for n in mb.topo_order(manifest):
        deps = manifest.targets[n].deps
        print(f"  {n}" + (f"  <- {', '.join(deps)}" if deps else ""))

    banner("2) COLD BUILD (empty cache -> everything rebuilds)")
    show(mb.Engine(manifest).build_all())

    banner("3) WARM BUILD (no changes -> all cache hits)")
    show(mb.Engine(manifest).build_all())

    banner("4) INCREMENTAL: edit src/greeting.txt -> only its sub-DAG rebuilds")
    (ROOT / "src" / "greeting.txt").write_text("hello\nworld\nfrom demo\n")
    show(mb.Engine(manifest).build_all())

    banner("5) EXPLAIN: why would 'app' rebuild now? (after restoring source)")
    sample.generate()  # restore greeting.txt; app is now stale vs the cache
    # Build deps so the engine knows their output hashes, then explain 'app'.
    engine = mb.Engine(manifest)
    for dep in mb.subgraph_order(manifest, "app")[:-1]:
        engine.build_target(dep)
    target = manifest.targets["app"]
    key, ih, do = engine.compute_key(target)
    reasons = engine.diff_reasons(target, key, ih, do)
    if reasons:
        print("  app WOULD REBUILD because:")
        for r in reasons:
            print(f"    - {r}")
    else:
        print("  app is a CACHE HIT")

    banner("6) HERMETICITY: a target that reads an UNDECLARED file is flagged")
    leak_manifest = json.loads((ROOT / "build.json").read_text())
    leak_manifest["targets"].append(
        {"name": "leaky", "inputs": ["src/name.txt"], "action": "leak", "output": "out/leaky.txt"}
    )
    leak_path = ROOT / "build_leak.json"
    leak_path.write_text(json.dumps(leak_manifest))
    secret = ROOT / "undeclared_secret.txt"
    secret.write_text("a file the action reads but never declared\n")
    try:
        lm = mb.Manifest.load(leak_path)
        eng = mb.Engine(lm)
        eng.cache.pop("leaky", None)  # ensure it actually runs
        results = {r.name: r for r in eng.build_all()}
        leaky = results["leaky"]
        if leaky.hermetic:
            print("  (unexpected) leaky target was hermetic")
        else:
            print("  leaky is NON-HERMETIC. Undeclared reads:")
            for p in leaky.undeclared_reads:
                print(f"    - {p}")
    finally:
        secret.unlink(missing_ok=True)
        leak_path.unlink(missing_ok=True)
        (ROOT / "out" / "leaky.txt").unlink(missing_ok=True)

    banner("DONE - now try the CLI yourself")
    print("  python3 mini_build.py graph")
    print("  python3 mini_build.py build all")
    print("  python3 mini_build.py --explain app")
    return 0


def show(results: list[mb.BuildResult]) -> None:
    for r in results:
        status = "REBUILT" if r.rebuilt else "cache-hit"
        line = f"  [{status:9}] {r.name}  ({r.output_hash[:12]})"
        if r.rebuilt and r.reasons:
            line += "   <- " + "; ".join(r.reasons)
        print(line)


if __name__ == "__main__":
    raise SystemExit(main())
