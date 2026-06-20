# Further learning resources

Last verified: 2026-06-21

A curated list of canonical, primary sources for this repo's named learning
technology: build-system fundamentals (dependency graphs, targets,
content-hash caches, hermeticity, incremental rebuilds) and the two real tools
those ideas come from, Bazel and Nix. Prefer these over blog posts; they are the
reference line this repo follows.

## Build-system fundamentals

- **Build Systems à la Carte (Mokhov, Mitchell, Peyton Jones)** —
  https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/
  The paper that frames build systems by two axes (rebuild strategy x scheduler)
  and shows where Make, Bazel, Nix, and Shake each sit. The clearest single
  explanation of *why* content hashing and dependency tracking matter.

- **Mike Bland / Build Systems chapter, "Software Engineering at Google"** —
  https://abseil.io/resources/swe-book
  Free book whose build-systems chapter explains why artifact-based,
  hermetic builds (the Bazel model) scale where task-based builds don't. Good on
  the dependency-graph and remote-cache motivation.

## Bazel

- **Bazel documentation (root)** — https://bazel.build
  The official docs home. Use it as the canonical reference for BUILD files,
  labels, targets, and rules.

- **Bazel build concepts and terminology** — https://bazel.build/concepts/build-ref
  Defines workspace, package, target, and label precisely — the vocabulary this
  repo's manifest model maps onto.

- **Bazel: dependency management / the build graph** —
  https://bazel.build/concepts/dependencies
  How Bazel derives the action graph from `deps`, the basis for its
  incrementality and the direct analog of `mini_build`'s DAG.

- **Bazel remote caching** — https://bazel.build/remote/caching
  How the content-addressed action cache is shared across machines and CI — the
  real version of this project's `--remote-cache` exercise.

- **Bazelisk (official launcher)** — https://github.com/bazelbuild/bazelisk
  The recommended way to install and pin a Bazel version; what this repo's
  `check_bazel.py` looks for.

## Nix

- **Nix / NixOS documentation (root)** — https://nixos.org
  The official home for Nix, the Nix language, and nixpkgs.

- **nix.dev (official learning portal)** — https://nix.dev
  Task-oriented official tutorials: dev shells, flakes, pinning, and packaging.
  The best starting point for the hands-on side of Nix.

- **Nix Reference Manual: derivations** — https://nix.dev/manual/nix
  The reference manual root; the derivation and store-path sections explain how
  an input hash determines an immutable `/nix/store` path — the content-addressed
  cache this project models.

- **The Purely Functional Software Deployment Model (Eelco Dolstra's thesis)** —
  https://edolstra.github.io/pubs/phd-thesis.pdf
  The original Nix thesis: why hashing all build inputs gives reproducible,
  content-addressed builds. The foundational text behind `/nix/store`.

## Language-native tools and CI (for the "when is heavy tooling worth it?" question)

- **GitHub Actions documentation** — https://docs.github.com/actions
  Canonical reference for CI; relevant to local-vs-CI parity and caching build
  outputs between runs.

- **Build tool comparison (this repo)** — ./build-tool-comparison.md
  The repo's own matrix of what each tool owns and when language-native tooling
  is enough versus when Bazel or Nix earns its keep.
