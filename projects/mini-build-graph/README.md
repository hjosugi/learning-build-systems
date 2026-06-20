# Mini Build Graph

A tiny, Bazel/Nix-flavored build **engine** in pure `python3` (stdlib only). It
exists to make the core ideas behind Bazel and Nix concrete and pokeable:

1. a **dependency DAG** of declared targets, topologically ordered, with cycle
   detection;
2. a **content-addressed cache** (hash of action + input contents + each
   dependency's output hash) that is **persisted between runs**;
3. **incremental rebuilds** — change one source, rebuild only the affected
   sub-DAG; `--explain TARGET` tells you *why*;
4. a **hermeticity check** — if an action reads a file it did not declare as an
   input, you get a warning.

This is intentionally different from `../native-build-runner`, which is just a
trivial "run these functions" target runner with no graph, no hashing, and no
cache. This project is the *engine* those concepts actually require.

Last verified: 2026-06-21

## What's here

| File | Role |
| --- | --- |
| `mini_build.py` | the engine + CLI (DAG, cache, hermeticity, `--explain`) |
| `sample.py` | generates sample sources + `build.json` so it runs out of the box |
| `demo.py` | end-to-end story: cold build, cache hit, incremental rebuild, explain, hermeticity |
| `test_mini_build.py` | `unittest` suite (topo order, cache hit, rebuild, cycles, hermeticity) |
| `build.json` | the sample manifest (a small compile/link-shaped DAG) |
| `src/` | sample source inputs |

The sample DAG (run `python3 mini_build.py graph` to see it):

```
name_obj      (concat src/name.txt)        \
greeting_obj  (concat src/greeting.txt)     >--> app (count_lines)  --> report (count_lines)
```

## Run

Everything below uses absolute paths and needs only `python3` (3.14). No pip, no
network.

The one-command tour (generates samples, then shows every concept):

```bash
python3 projects/mini-build-graph/demo.py
```

Or drive the CLI yourself:

```bash
# 1. generate sample sources + build.json (idempotent)
python3 projects/mini-build-graph/sample.py

# 2. see the dependency graph in topological order
python3 projects/mini-build-graph/mini_build.py \
  --manifest projects/mini-build-graph/build.json graph

# 3. first build: everything REBUILT
python3 projects/mini-build-graph/mini_build.py \
  --manifest projects/mini-build-graph/build.json build all

# 4. second build, no changes: all cache-hit (cache persisted to .mini_build_cache.json)
python3 projects/mini-build-graph/mini_build.py \
  --manifest projects/mini-build-graph/build.json build all

# 5. touch a source, then explain why a downstream target will rebuild
printf 'hello\nworld\nagain\n' > projects/mini-build-graph/src/greeting.txt
python3 projects/mini-build-graph/mini_build.py \
  --manifest projects/mini-build-graph/build.json --explain app

# 6. incremental rebuild: only greeting_obj -> app -> report rebuild; name_obj stays cached
python3 projects/mini-build-graph/mini_build.py \
  --manifest projects/mini-build-graph/build.json build all
```

`--explain TARGET` prints either `CACHE HIT` or the exact list of changed
inputs/deps that would force a rebuild. `build TARGET` builds only that target's
sub-DAG; `build all` builds the whole graph; `--force` ignores the cache.

## Test

Non-interactive; exits non-zero on failure:

```bash
python3 -m unittest discover -s projects/mini-build-graph -p 'test_*.py' -v
```

## How it works (the load-bearing details)

- **Build key (content address).** `Engine.compute_key` hashes the action name,
  the target's output path, the SHA-256 of each declared input's *contents*, and
  each dependency's *output hash*. Because dependency output hashes are folded
  in, a change anywhere upstream changes the key downstream — that is what makes
  the rebuild set correct. Identical inputs always produce an identical key, so
  the same work maps to the same cache slot. This is exactly how a Nix store
  path is derived from its inputs and how Bazel keys its action cache.

- **Cache hit rule.** A target is skipped iff its build key equals the persisted
  key *and* its output artifact still exists on disk. Delete an output and it
  rebuilds (see `test_missing_output_forces_rebuild`).

- **Hermeticity check.** During an action, `OpenTracer` patches `io.open` (which
  both `open()` and `pathlib.Path.read_text/read_bytes` route through) and
  records every read path. Any read that is not a declared input or a
  dependency's output is reported as an undeclared dependency. Real Bazel/Nix
  *enforce* this with an OS sandbox; we *observe* it, which is enough to teach
  why undeclared reads are the root cause of "works on my machine."

## Upgrade path

This engine is a learning model. Here is how each concept maps to the real heavy
tools, and exactly what you'd swap in.

### To Bazel

| Concept here | Bazel equivalent | How to swap in |
| --- | --- | --- |
| `build.json` targets | `BUILD.bazel` files with rule targets | Replace the manifest with `BUILD.bazel`; each `target` becomes e.g. `py_library` / `py_binary` / `genrule`. |
| `name` | a **label** like `//pkg:app` | Targets are addressed by package-relative labels, not bare names. |
| `inputs` | `srcs` attribute | List source files in `srcs`. |
| `deps` | `deps` attribute | Bazel derives the action graph from `deps`. |
| (no scoping here) | `visibility` | Add `visibility = ["//some:pkg"]` to control who may depend on a target. |
| `action` functions | rule implementations / `genrule cmd` | Real actions run a hermetic command line in a sandbox. |
| `compute_key` + `.mini_build_cache.json` | the action cache | Bazel keys actions on action + inputs; identical to our build key idea. |
| our hermeticity warning | the **sandbox**, which *enforces* it | Undeclared reads fail the build instead of warning. |
| local cache file | **remote cache** | `bazel build --remote_cache=grpc://...` shares the content-addressed cache across machines/CI. |
| `--explain app` | `bazel build --explain=log.txt --verbose_explanations` | Bazel writes why each action ran. |

Try it against this repo's `../bazel-python-lab` (it already has `MODULE.bazel`
and `BUILD.bazel`):

```bash
cd projects/bazel-python-lab
bazel build //...        # bazelisk recommended; see check_bazel.py
bazel test  //...
```

### To Nix

| Concept here | Nix equivalent | How to swap in |
| --- | --- | --- |
| a target | a **derivation** (`.drv`) | `pkgs.stdenv.mkDerivation { ... }` describes inputs + a build command. |
| `inputs` + `deps` | `src` + `buildInputs` | All inputs are hashed; nothing outside them is visible. |
| `compute_key` (input hash) | the **derivation hash** | The hash of all inputs determines the output path. |
| `.mini_build_cache.json` | **`/nix/store`** (content-addressed) | The store *is* the cache: a given input hash maps to one immutable store path. |
| our hermeticity warning | the Nix **build sandbox** | Builds run with no network and a pruned filesystem; undeclared reads simply aren't there. |
| sharing the cache | **binary cache** (e.g. cache.nixos.org) | If the input hash exists in a substituter, Nix downloads instead of rebuilding. |

Try it against this repo's `../nix-devshell-lab`:

```bash
cd projects/nix-devshell-lab
nix develop              # see check_nix.py if Nix isn't installed
```

### When the heavy tool earns its keep

- **Language-native tools are enough** (Maven/Gradle, pnpm, uv, Go modules, plus
  Make/just as command runners) when you have one language, one machine story,
  and your tool's own cache already gives correct incremental builds. Most repos
  live here.
- **Reach for Nix** when *environment reproducibility* is the pain: "works on my
  machine," divergent toolchain versions, or local/CI drift. Nix pins the whole
  toolchain, not just library dependencies.
- **Reach for Bazel** when the *build graph itself* is the pain: a large,
  multi-language repo where you need a single dependency graph, fine-grained
  incrementality, a shared remote cache across many engineers/CI, and hermetic
  actions enforced (not just hoped for).
- **The cost** is real: BUILD files, rule authoring, and a learning curve
  (Bazel); a new language and the store mental model (Nix). Adopt them when the
  graph/reproducibility benefit outweighs that, not by default. See
  `../../docs/build-tool-comparison.md`.

## Exercises

1. **Add a parallel scheduler.** Targets with no dependency relationship can run
   concurrently. Group `topo_order` into "levels" (all targets whose deps are
   already built) and run each level with `concurrent.futures.ThreadPoolExecutor`.
   Confirm the cache results are identical to the serial build.

2. **Add a real command action.** Add an action that runs a subprocess (e.g.
   `python3 -c ...` or a compiler) instead of an in-process function. Capture
   `stdout` as the output. Then make the hermeticity tracer cover subprocess
   reads too (hint: you can't patch `io.open` in a child process — research how
   Bazel/Nix use OS sandboxes, and write up why a pure-stdlib tracer can't fully
   enforce hermeticity across process boundaries).

3. **Detect output collisions.** Two targets that declare the same `output` path
   will clobber each other. Add a manifest-validation pass that rejects this, and
   add a test. (Bazel rejects this as a "conflicting actions" error.)

4. **Make the cache content-addressed by output, like `/nix/store`.** Instead of
   overwriting `out/app.txt`, store each output at `cache/<output_hash>` and
   symlink/copy the named output to it. Show that switching a source back to a
   previous version is now an instant cache restore with no action run — the Nix
   "the store already has it" behavior.

5. **Add a `--remote-cache DIR` flag.** Before running an action, look up the
   build key in a shared directory; on a miss, run and write the output there
   keyed by the build key. Run two builds pointed at the same dir from two
   different working copies and watch the second be all cache hits — a minimal
   model of Bazel's remote cache.
```
