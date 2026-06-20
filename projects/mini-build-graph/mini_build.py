"""mini_build.py - a tiny Bazel/Nix-flavored build engine (python3 stdlib only).

This is a *teaching* build engine. It deliberately implements, in a few hundred
readable lines, the four ideas that make Bazel and Nix different from a plain
script runner (which is all that `native-build-runner` in this repo is):

  1. A dependency DAG of declared TARGETS, topologically ordered, with cycle
     detection. (Bazel: the action graph derived from BUILD files. Nix: the
     dependency graph of derivations.)

  2. A CONTENT-ADDRESSED cache. Each target gets a "build key" = a hash of its
     action, its declared input files' contents, AND the output hashes of every
     dependency. If the key is unchanged since last run we SKIP the action.
     (Bazel: the analysis/action cache keyed on action + inputs. Nix: the store
     path is derived from the hash of the derivation inputs; /nix/store *is* the
     cache.)

  3. INCREMENTAL rebuilds. Because the key folds in dependencies' output hashes,
     changing one source file rebuilds exactly the affected sub-DAG and nothing
     else. `--explain TARGET` reports *why* a target rebuilt or was a cache hit.

  4. A HERMETICITY check. A hermetic action reads only its declared inputs. We
     intercept file opens during the action and warn about any read of a file
     that was not declared as an input or produced by a dependency. (Bazel runs
     actions in a sandbox that *enforces* this; Nix builds in an isolated
     sandbox with no network and a pruned filesystem.)

The cache is persisted to .mini_build_cache.json next to the manifest, so a
second run with no changes is all cache hits.

Run `python3 mini_build.py --help` for the CLI. See README.md for the upgrade
path to real Bazel / Nix.
"""

from __future__ import annotations

import argparse
import builtins
import hashlib
import io
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

# --------------------------------------------------------------------------- #
# Manifest model
# --------------------------------------------------------------------------- #
# A "target" is the unit of build work, exactly like a Bazel rule target or a
# Nix derivation. It declares:
#   - name:    a unique label (cf. a Bazel label like //pkg:lib)
#   - inputs:  source files it reads (paths relative to the manifest dir)
#   - deps:    names of other targets whose outputs it consumes
#   - action:  a key naming a python function in the ACTIONS registry that
#              produces the output. Real systems run a command line; we keep the
#              action in-process so the demo needs no compiler toolchain.
#   - output:  the path this target writes (relative to the manifest dir)


@dataclass(frozen=True)
class Target:
    name: str
    inputs: tuple[str, ...] = ()
    deps: tuple[str, ...] = ()
    action: str = "noop"
    output: str = ""

    @staticmethod
    def from_dict(d: dict) -> "Target":
        return Target(
            name=d["name"],
            inputs=tuple(d.get("inputs", ())),
            deps=tuple(d.get("deps", ())),
            action=d.get("action", "noop"),
            output=d.get("output", ""),
        )


@dataclass
class Manifest:
    root: Path  # directory the manifest lives in; all paths are relative to it
    targets: dict[str, Target]

    @staticmethod
    def load(path: Path) -> "Manifest":
        data = json.loads(path.read_text())
        targets = {}
        for raw in data["targets"]:
            t = Target.from_dict(raw)
            if t.name in targets:
                raise ValueError(f"duplicate target name: {t.name}")
            targets[t.name] = t
        return Manifest(root=path.resolve().parent, targets=targets)


# --------------------------------------------------------------------------- #
# Dependency graph: topo sort + cycle detection
# --------------------------------------------------------------------------- #


class CycleError(Exception):
    """Raised when the target graph contains a dependency cycle."""


def topo_order(manifest: Manifest) -> list[str]:
    """Return target names in dependency order (deps before dependents).

    Uses depth-first search with three colors so we can *name the cycle* when we
    find one, which is what makes a build tool's error message useful. This is
    the same job Bazel does when it loads BUILD files and Nix does when it
    instantiates derivations.
    """
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {n: WHITE for n in manifest.targets}
    order: list[str] = []
    stack_trace: list[str] = []

    def visit(name: str) -> None:
        if name not in manifest.targets:
            raise ValueError(f"unknown dependency target: {name!r}")
        if color[name] == BLACK:
            return
        if color[name] == GREY:
            # Found a back-edge -> cycle. Slice the trace to show only the loop.
            i = stack_trace.index(name)
            cycle = stack_trace[i:] + [name]
            raise CycleError("dependency cycle: " + " -> ".join(cycle))
        color[name] = GREY
        stack_trace.append(name)
        for dep in manifest.targets[name].deps:
            visit(dep)
        stack_trace.pop()
        color[name] = BLACK
        order.append(name)

    for n in sorted(manifest.targets):  # sorted -> deterministic output
        visit(n)
    return order


def subgraph_order(manifest: Manifest, goal: str) -> list[str]:
    """Topo order restricted to `goal` and its transitive dependencies."""
    if goal not in manifest.targets:
        raise ValueError(f"unknown target: {goal!r}")
    full = topo_order(manifest)  # also validates: no cycles, deps exist
    needed: set[str] = set()

    def collect(name: str) -> None:
        if name in needed:
            return
        needed.add(name)
        for dep in manifest.targets[name].deps:
            collect(dep)

    collect(goal)
    return [n for n in full if n in needed]


# --------------------------------------------------------------------------- #
# Hashing helpers (the "content-addressed" part)
# --------------------------------------------------------------------------- #


def hash_bytes(*chunks: bytes) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(len(c).to_bytes(8, "big"))  # length-prefix to avoid ambiguity
        h.update(c)
    return h.hexdigest()


def hash_file(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hash_bytes(path.read_bytes())


# --------------------------------------------------------------------------- #
# Hermeticity: a file-open tracer
# --------------------------------------------------------------------------- #
# A hermetic action reads only what it declared. We can't sandbox the OS in pure
# stdlib, but we CAN observe: temporarily wrap the file-open primitive so every
# read path is recorded. Anything read that was not declared as an input or
# produced by a dependency is an undeclared dependency -> a hermeticity
# violation.
#
# We patch io.open rather than builtins.open because both the builtin open()
# AND pathlib's Path.open()/read_text()/read_bytes() funnel through io.open.
# Patching only builtins.open would miss Path-based reads, which silently lets
# non-hermetic actions slip past the check. (builtins.open IS io.open, but
# pathlib resolves the name through the io module, so we must patch io.open and
# keep builtins.open in sync.)


class OpenTracer:
    def __init__(self) -> None:
        self.reads: set[str] = set()
        self._real_open: Callable | None = None

    def __enter__(self) -> "OpenTracer":
        self._real_open = io.open
        tracer = self

        def traced_open(file, mode="r", *args, **kwargs):  # noqa: ANN001
            try:
                # Record reads only (modes without 'w'/'a'/'x'/'+' create/append).
                if isinstance(file, (str, os.PathLike)) and not any(
                    m in mode for m in ("w", "a", "x", "+")
                ):
                    tracer.reads.add(str(Path(file).resolve()))
            except Exception:
                pass
            return tracer._real_open(file, mode, *args, **kwargs)

        io.open = traced_open  # type: ignore[assignment]
        builtins.open = traced_open  # type: ignore[assignment]
        return self

    def __exit__(self, *exc) -> None:
        if self._real_open is not None:
            io.open = self._real_open  # type: ignore[assignment]
            builtins.open = self._real_open  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Actions: what a target actually does
# --------------------------------------------------------------------------- #
# In a real build the action is a command line (gcc, javac, ...). Here actions
# are small python functions so the demo is self-contained. Each takes a build
# Context and writes its declared output. The hermeticity tracer watches the
# files they open.


@dataclass
class Context:
    manifest: Manifest
    target: Target

    def in_path(self, rel: str) -> Path:
        return self.manifest.root / rel

    def read_input(self, rel: str) -> str:
        # Uses the (possibly traced) builtins.open via Path.read_text.
        return (self.manifest.root / rel).read_text()

    def write_output(self, text: str) -> None:
        out = self.manifest.root / self.target.output
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)


ActionFn = Callable[[Context], None]
ACTIONS: dict[str, ActionFn] = {}


def action(name: str) -> Callable[[ActionFn], ActionFn]:
    def deco(fn: ActionFn) -> ActionFn:
        ACTIONS[name] = fn
        return fn

    return deco


@action("noop")
def _noop(ctx: Context) -> None:
    ctx.write_output("")


@action("concat")
def _concat(ctx: Context) -> None:
    """Concatenate all declared inputs (a stand-in for 'compile these sources')."""
    parts = [ctx.read_input(i) for i in ctx.target.inputs]
    ctx.write_output("".join(parts))


@action("count_lines")
def _count_lines(ctx: Context) -> None:
    """Read dependency outputs + inputs and emit a small report (a 'link' step)."""
    text = ""
    for dep_name in ctx.target.deps:
        dep = ctx.manifest.targets[dep_name]
        if dep.output:
            text += ctx.read_input(dep.output)
    for i in ctx.target.inputs:
        text += ctx.read_input(i)
    n = text.count("\n")
    ctx.write_output(f"lines={n}\nbytes={len(text)}\n")


@action("leak")
def _leak(ctx: Context) -> None:
    """Demo of a NON-hermetic action: reads an undeclared file on purpose.

    Used by the hermeticity demo/tests. A real action that did this would build
    fine on your machine and mysteriously break on a teammate's or in CI.
    """
    body = "".join(ctx.read_input(i) for i in ctx.target.inputs)
    secret = ctx.manifest.root / "undeclared_secret.txt"
    if secret.exists():
        body += secret.read_text()  # <-- undeclared read; tracer will catch it
    ctx.write_output(body)


# --------------------------------------------------------------------------- #
# The cache and the engine
# --------------------------------------------------------------------------- #


@dataclass
class CacheEntry:
    build_key: str
    output_hash: str
    inputs: dict[str, str] = field(default_factory=dict)  # rel path -> hash
    dep_outputs: dict[str, str] = field(default_factory=dict)  # dep name -> hash
    action: str = ""


@dataclass
class BuildResult:
    name: str
    rebuilt: bool
    reasons: list[str]
    output_hash: str
    hermetic: bool = True
    undeclared_reads: list[str] = field(default_factory=list)


class Engine:
    CACHE_FILE = ".mini_build_cache.json"

    def __init__(self, manifest: Manifest) -> None:
        self.manifest = manifest
        self.cache_path = manifest.root / self.CACHE_FILE
        self.cache: dict[str, CacheEntry] = self._load_cache()
        # output hashes computed this run, used to key dependents
        self.output_hashes: dict[str, str] = {}

    # -- cache persistence --------------------------------------------------- #
    def _load_cache(self) -> dict[str, CacheEntry]:
        if not self.cache_path.exists():
            return {}
        raw = json.loads(self.cache_path.read_text())
        return {k: CacheEntry(**v) for k, v in raw.items()}

    def _save_cache(self) -> None:
        serializable = {k: vars(v) for k, v in self.cache.items()}
        self.cache_path.write_text(json.dumps(serializable, indent=2) + "\n")

    # -- the build key (content address) ------------------------------------- #
    def compute_key(self, target: Target) -> tuple[str, dict[str, str], dict[str, str]]:
        """Build key = hash(action + sorted input hashes + sorted dep output hashes).

        This is the heart of content addressing. Two builds with the same inputs
        produce the same key, hence the same cache slot -- exactly how a Nix
        store path or a Bazel action cache key is derived.
        """
        input_hashes = {
            rel: hash_file(self.manifest.root / rel) for rel in target.inputs
        }
        dep_outputs = {dep: self.output_hashes[dep] for dep in target.deps}
        material = json.dumps(
            {
                "action": target.action,
                "output": target.output,
                "inputs": dict(sorted(input_hashes.items())),
                "deps": dict(sorted(dep_outputs.items())),
            },
            sort_keys=True,
        ).encode()
        return hash_bytes(material), input_hashes, dep_outputs

    # -- why did this (not) rebuild? ----------------------------------------- #
    def diff_reasons(
        self,
        target: Target,
        new_key: str,
        input_hashes: dict[str, str],
        dep_outputs: dict[str, str],
    ) -> list[str]:
        prev = self.cache.get(target.name)
        if prev is None:
            return ["no cache entry (first build)"]
        if prev.build_key == new_key:
            return []
        reasons: list[str] = []
        if prev.action != target.action:
            reasons.append(f"action changed: {prev.action!r} -> {target.action!r}")
        for rel, h in input_hashes.items():
            old = prev.inputs.get(rel)
            if old is None:
                reasons.append(f"new input: {rel}")
            elif old != h:
                reasons.append(f"input changed: {rel}")
        for rel in prev.inputs:
            if rel not in input_hashes:
                reasons.append(f"input removed: {rel}")
        for dep, h in dep_outputs.items():
            old = prev.dep_outputs.get(dep)
            if old is None:
                reasons.append(f"new dep: {dep}")
            elif old != h:
                reasons.append(f"dep rebuilt: {dep}")
        if not reasons:
            reasons.append("build key changed")
        return reasons

    # -- run a single target ------------------------------------------------- #
    def build_target(self, name: str, *, force: bool = False) -> BuildResult:
        target = self.manifest.targets[name]
        key, input_hashes, dep_outputs = self.compute_key(target)
        reasons = self.diff_reasons(target, key, input_hashes, dep_outputs)
        prev = self.cache.get(name)

        # Cache hit: key unchanged and the output still exists on disk.
        out_path = self.manifest.root / target.output if target.output else None
        output_present = out_path is None or out_path.exists()
        if not force and prev and prev.build_key == key and output_present:
            self.output_hashes[name] = prev.output_hash
            return BuildResult(name, rebuilt=False, reasons=[], output_hash=prev.output_hash)

        # Cache miss: run the action under the hermeticity tracer.
        ctx = Context(self.manifest, target)
        fn = ACTIONS.get(target.action)
        if fn is None:
            raise ValueError(f"unknown action {target.action!r} for target {name!r}")
        with OpenTracer() as tracer:
            fn(ctx)

        # Hermeticity check: every read must be a declared input or a dep output.
        allowed = {str((self.manifest.root / i).resolve()) for i in target.inputs}
        for dep in target.deps:
            dep_out = self.manifest.targets[dep].output
            if dep_out:
                allowed.add(str((self.manifest.root / dep_out).resolve()))
        undeclared = sorted(
            r
            for r in tracer.reads
            if r not in allowed and r != str(self.cache_path.resolve())
        )
        hermetic = not undeclared

        output_hash = hash_file(out_path) if out_path else hash_bytes(b"")
        self.output_hashes[name] = output_hash
        self.cache[name] = CacheEntry(
            build_key=key,
            output_hash=output_hash,
            inputs=input_hashes,
            dep_outputs=dep_outputs,
            action=target.action,
        )
        return BuildResult(
            name,
            rebuilt=True,
            reasons=reasons,
            output_hash=output_hash,
            hermetic=hermetic,
            undeclared_reads=undeclared,
        )

    # -- run a goal and its sub-DAG ----------------------------------------- #
    def build(self, goal: str, *, force: bool = False) -> list[BuildResult]:
        order = subgraph_order(self.manifest, goal)
        results = [self.build_target(n, force=force) for n in order]
        self._save_cache()
        return results

    def build_all(self, *, force: bool = False) -> list[BuildResult]:
        order = topo_order(self.manifest)
        results = [self.build_target(n, force=force) for n in order]
        self._save_cache()
        return results


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def _default_manifest() -> Path:
    return Path(__file__).resolve().parent / "build.json"


def _print_results(results: list[BuildResult]) -> None:
    for r in results:
        status = "REBUILT" if r.rebuilt else "cache-hit"
        print(f"  [{status:9}] {r.name}  ({r.output_hash[:12]})")
        if r.rebuilt and r.reasons:
            for reason in r.reasons:
                print(f"               reason: {reason}")
        if not r.hermetic:
            print(f"               WARNING: non-hermetic! undeclared reads:")
            for path in r.undeclared_reads:
                print(f"                 - {path}")


def cmd_build(args: argparse.Namespace) -> int:
    manifest = Manifest.load(Path(args.manifest))
    engine = Engine(manifest)
    if args.target == "all":
        results = engine.build_all(force=args.force)
    else:
        results = engine.build(args.target, force=args.force)
    print(f"build goal: {args.target}")
    _print_results(results)
    violations = [r for r in results if not r.hermetic]
    rebuilt = sum(1 for r in results if r.rebuilt)
    print(f"summary: {rebuilt} rebuilt, {len(results) - rebuilt} cached", end="")
    if violations:
        print(f", {len(violations)} hermeticity warning(s)")
    else:
        print()
    return 0


def cmd_graph(args: argparse.Namespace) -> int:
    manifest = Manifest.load(Path(args.manifest))
    order = topo_order(manifest)
    print("topological order (deps first):")
    for n in order:
        deps = manifest.targets[n].deps
        suffix = f"  <- {', '.join(deps)}" if deps else ""
        print(f"  {n}{suffix}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    """Dry-run a single target's decision WITHOUT running its action.

    Reports either 'cache hit' or the precise list of changed inputs/deps that
    would force a rebuild. This is the diagnostic Bazel gives via
    --explain/--verbose_explanations and that you reconstruct in Nix by diffing
    derivation .drv hashes.
    """
    manifest = Manifest.load(Path(args.manifest))
    engine = Engine(manifest)
    # We must know dependency output hashes to compute this target's key, so
    # build the deps (incrementally; they'll be cache hits if unchanged).
    order = subgraph_order(manifest, args.target)
    for dep in order[:-1]:
        engine.build_target(dep)
    target = manifest.targets[args.target]
    key, input_hashes, dep_outputs = engine.compute_key(target)
    reasons = engine.diff_reasons(target, key, input_hashes, dep_outputs)
    out_path = manifest.root / target.output if target.output else None
    output_present = out_path is None or out_path.exists()
    print(f"explain: {args.target}")
    if not reasons and output_present:
        prev = engine.cache.get(args.target)
        h = prev.output_hash[:12] if prev else "?"
        print(f"  CACHE HIT - build key {key[:12]} unchanged; output {h}")
    else:
        if not output_present:
            reasons = reasons or ["output artifact missing on disk"]
        print(f"  WOULD REBUILD - build key would change to {key[:12]}")
        for reason in reasons:
            print(f"    - {reason}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mini_build",
        description="A tiny Bazel/Nix-flavored build engine: DAG, content cache, "
        "incremental rebuild, hermeticity check.",
    )
    p.add_argument(
        "--manifest",
        default=str(_default_manifest()),
        help="path to the build manifest JSON (default: build.json next to this file)",
    )
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build a target (or 'all') incrementally")
    b.add_argument("target", help="target name, or 'all'")
    b.add_argument("--force", action="store_true", help="ignore cache, rebuild everything")
    b.set_defaults(func=cmd_build)

    g = sub.add_parser("graph", help="print the topological order of the DAG")
    g.set_defaults(func=cmd_graph)

    e = sub.add_parser("explain", help="explain why a target would rebuild or is cached")
    e.add_argument("target", help="target name")
    e.set_defaults(func=cmd_explain)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    # Support `--explain TARGET` as an alias for `explain TARGET`, matching the
    # task's spec, while keeping the cleaner subcommand form too.
    raw = list(sys.argv[1:] if argv is None else argv)
    if "--explain" in raw:
        i = raw.index("--explain")
        rest = raw[:i] + raw[i + 2 :]
        target = raw[i + 1] if i + 1 < len(raw) else None
        if target is None:
            parser.error("--explain requires a TARGET")
        return cmd_explain(parser.parse_args(rest + ["explain", target]))
    args = parser.parse_args(raw)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
