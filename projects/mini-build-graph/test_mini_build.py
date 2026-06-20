"""Unit tests for the mini build engine.

Covers the four concepts the project teaches:
  - topological order correctness (deps before dependents)
  - cycle detection (with a useful message)
  - cache hit when nothing changed (incremental build)
  - rebuild propagation when a source changes
  - the hermeticity check catching an undeclared read

Run non-interactively:  python3 -m unittest -v   (exits non-zero on failure)
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import mini_build as mb


def write_manifest(root: Path, targets: list[dict]) -> Path:
    path = root / "build.json"
    path.write_text(json.dumps({"targets": targets}))
    return path


def chain_manifest(root: Path) -> mb.Manifest:
    """a -> b -> c (c depends on b depends on a), each a concat of one source."""
    (root / "src").mkdir(exist_ok=True)
    (root / "src" / "a.txt").write_text("alpha\n")
    targets = [
        {"name": "a", "inputs": ["src/a.txt"], "action": "concat", "output": "out/a.txt"},
        {"name": "b", "deps": ["a"], "action": "count_lines", "output": "out/b.txt"},
        {"name": "c", "deps": ["b"], "action": "count_lines", "output": "out/c.txt"},
    ]
    return mb.Manifest.load(write_manifest(root, targets))


class TopoOrderTests(unittest.TestCase):
    def test_deps_come_before_dependents(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            order = mb.topo_order(manifest)
            self.assertEqual(order, ["a", "b", "c"])

    def test_order_is_deterministic_with_parallel_branches(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "x.txt").write_text("x\n")
            (root / "src" / "y.txt").write_text("y\n")
            targets = [
                {"name": "x", "inputs": ["src/x.txt"], "action": "concat", "output": "out/x"},
                {"name": "y", "inputs": ["src/y.txt"], "action": "concat", "output": "out/y"},
                {"name": "top", "deps": ["x", "y"], "action": "count_lines", "output": "out/t"},
            ]
            manifest = mb.Manifest.load(write_manifest(root, targets))
            order = mb.topo_order(manifest)
            self.assertLess(order.index("x"), order.index("top"))
            self.assertLess(order.index("y"), order.index("top"))
            # deterministic across calls
            self.assertEqual(order, mb.topo_order(manifest))

    def test_subgraph_only_pulls_needed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            # building b should not require c
            self.assertEqual(mb.subgraph_order(manifest, "b"), ["a", "b"])


class CycleTests(unittest.TestCase):
    def test_cycle_is_detected_and_named(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            targets = [
                {"name": "a", "deps": ["c"], "action": "noop", "output": "out/a"},
                {"name": "b", "deps": ["a"], "action": "noop", "output": "out/b"},
                {"name": "c", "deps": ["b"], "action": "noop", "output": "out/c"},
            ]
            manifest = mb.Manifest.load(write_manifest(root, targets))
            with self.assertRaises(mb.CycleError) as ctx:
                mb.topo_order(manifest)
            self.assertIn("cycle", str(ctx.exception))

    def test_unknown_dependency_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            targets = [{"name": "a", "deps": ["ghost"], "action": "noop", "output": "out/a"}]
            manifest = mb.Manifest.load(write_manifest(root, targets))
            with self.assertRaises(ValueError):
                mb.topo_order(manifest)


class CacheTests(unittest.TestCase):
    def test_cache_hit_when_nothing_changes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            first = mb.Engine(manifest).build_all()
            self.assertTrue(all(r.rebuilt for r in first))
            # fresh engine reloads the persisted cache from disk
            second = mb.Engine(manifest).build_all()
            self.assertTrue(all(not r.rebuilt for r in second), [r.name for r in second if r.rebuilt])

    def test_cache_persists_between_engine_instances(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = chain_manifest(root)
            mb.Engine(manifest).build_all()
            self.assertTrue((root / mb.Engine.CACHE_FILE).exists())

    def test_change_rebuilds_only_affected_subdag(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = chain_manifest(root)
            mb.Engine(manifest).build_all()
            # touch the leaf source -> a, b, c must all rebuild (key folds deps)
            (root / "src" / "a.txt").write_text("alpha changed\n")
            results = {r.name: r for r in mb.Engine(manifest).build_all()}
            self.assertTrue(results["a"].rebuilt)
            self.assertIn("input changed: src/a.txt", results["a"].reasons)
            self.assertTrue(results["b"].rebuilt)
            self.assertIn("dep rebuilt: a", results["b"].reasons)

    def test_unrelated_target_stays_cached_on_change(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "x.txt").write_text("x\n")
            (root / "src" / "y.txt").write_text("y\n")
            targets = [
                {"name": "x", "inputs": ["src/x.txt"], "action": "concat", "output": "out/x"},
                {"name": "y", "inputs": ["src/y.txt"], "action": "concat", "output": "out/y"},
            ]
            manifest = mb.Manifest.load(write_manifest(root, targets))
            mb.Engine(manifest).build_all()
            (root / "src" / "x.txt").write_text("x changed\n")
            results = {r.name: r for r in mb.Engine(manifest).build_all()}
            self.assertTrue(results["x"].rebuilt)
            self.assertFalse(results["y"].rebuilt)  # y is independent -> still cached

    def test_force_rebuilds_everything(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            mb.Engine(manifest).build_all()
            forced = mb.Engine(manifest).build_all(force=True)
            self.assertTrue(all(r.rebuilt for r in forced))

    def test_missing_output_forces_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            manifest = chain_manifest(root)
            mb.Engine(manifest).build_all()
            (root / "out" / "a.txt").unlink()  # someone deleted an artifact
            results = {r.name: r for r in mb.Engine(manifest).build_all()}
            self.assertTrue(results["a"].rebuilt)


class HermeticityTests(unittest.TestCase):
    def test_undeclared_read_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "src").mkdir()
            (root / "src" / "n.txt").write_text("n\n")
            (root / "undeclared_secret.txt").write_text("secret\n")
            targets = [
                {"name": "leaky", "inputs": ["src/n.txt"], "action": "leak", "output": "out/l"},
            ]
            manifest = mb.Manifest.load(write_manifest(root, targets))
            results = mb.Engine(manifest).build_all()
            leaky = results[0]
            self.assertFalse(leaky.hermetic)
            self.assertTrue(any("undeclared_secret.txt" in p for p in leaky.undeclared_reads))

    def test_declared_only_action_is_hermetic(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            results = mb.Engine(manifest).build_all()
            self.assertTrue(all(r.hermetic for r in results))


class KeyTests(unittest.TestCase):
    def test_same_inputs_same_key(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            manifest = chain_manifest(Path(d))
            e = mb.Engine(manifest)
            e.build_all()  # populates output_hashes for deps
            k1, _, _ = e.compute_key(manifest.targets["a"])
            k2, _, _ = e.compute_key(manifest.targets["a"])
            self.assertEqual(k1, k2)


if __name__ == "__main__":
    unittest.main()
