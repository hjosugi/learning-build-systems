# Learning Build Systems

Build tools and reproducible development environment experiments with Bazel, Nix, language-native build tools, and CI integration.

Last verified: 2026-06-21

## Development Environment

If Bazel/Bazelisk, Groovy, or Java are missing locally, enter the Nix shell:

```bash
nix develop
```

## Runnable Starter Project

Run the tiny build runner first, then port the same target graph to Make, Bazel, and Nix:

```bash
python3 projects/native-build-runner/build.py all
python3 projects/native-build-runner/test_build.py
python3 projects/groovy-unit-test-lab/check_groovy.py
```

Then build the real thing: a tiny Bazel/Nix-flavored build engine with a
dependency DAG, a persisted content-addressed cache, incremental rebuilds,
`--explain`, and a hermeticity check. See
[projects/mini-build-graph/README.md](projects/mini-build-graph/README.md):

```bash
python3 projects/mini-build-graph/demo.py
python3 -m unittest discover -s projects/mini-build-graph -p 'test_*.py'
```

Groovy hands-on:

```bash
groovy projects/groovy-unit-test-lab/CalculatorTest.groovy
```

## Target Hands-On Projects

Bazel:

```bash
python3 projects/bazel-python-lab/check_bazel.py
```

When Bazel or Bazelisk is installed:

```bash
cd projects/bazel-python-lab
bazel test //...
```

Nix:

```bash
python3 projects/nix-devshell-lab/check_nix.py
```

When Nix is installed:

```bash
cd projects/nix-devshell-lab
nix develop
```

## Why This Repo Exists

Application repos should teach application code. Platform repos should teach operations. This repo is for the layer in between:

- how code is built
- how developer environments are created
- how dependencies are pinned
- how multi-language projects stay reproducible
- how CI runs the same build as local development

## Baseline

- Bazel official docs as the current reference line
- Bazelisk as the preferred Bazel launcher
- Nix and nix.dev official docs as the current reference line
- Nix flakes for pinned development environments where appropriate
- GitHub Actions for CI experiments

## What This Repo Teaches

This repo answers one practical question: when does extra build tooling pay for itself?

Each example should compare:

- language-native tool only
- Bazel or Nix enhancement
- local developer experience
- CI parity
- cache and reproducibility benefits
- extra complexity introduced

The goal is not to force Bazel or Nix everywhere. The goal is to learn when they improve a project and when ordinary Maven, Gradle, pnpm, uv, or Go modules are enough.

## Learning Path

1. Build system fundamentals
2. Bazel basics: workspace, packages, targets, labels, BUILD files
3. Bazel for Java, Go, TypeScript, and Python samples
4. Nix basics: shells, flakes, pinning, reproducible environments
5. Nix dev shells for existing projects
6. Language-native tools: Maven/Gradle, pnpm, uv, Go modules
7. CI integration and build cache notes
8. Tradeoffs: when Bazel/Nix helps and when it is too much

## Repository Profile

See [docs/repository-profile.md](docs/repository-profile.md) for GitHub description, topics, public safety notes, and first milestones.

## Planned Structure

```text
examples/
  bazel-java/
  bazel-go/
  bazel-typescript/
  bazel-python/
  nix-devshell-node/
  nix-devshell-python/
  nix-devshell-java/
  polyglot-bazel-nix/
docs/
  2026-learning-items.md
  build-tool-comparison.md
  environment-strategy.md
  troubleshooting.md
templates/
  github-actions/
  devshells/
```

## What Belongs Here

- Bazel experiments
- Nix and flakes experiments
- reproducible dev shells
- build cache notes
- CI build templates
- environment setup comparisons
- multi-language build strategy

## What Does Not Belong Here

- application feature code
- deployment and runbooks; put those in `learning-platform-engineering`
- design pattern examples; put those in `learning-design-patterns-polyglot`

## Study Loop

1. build a tiny native project first
2. add a Bazel or Nix version
3. write down what became more reproducible
4. write down what became harder
5. add CI only after the local command is clear

## First Milestones

1. Add one Java Bazel example and compare it with Maven/Gradle.
2. Add one Go Bazel example and compare it with Go modules.
3. Add one Node dev shell and one Python dev shell with Nix.
4. Add a troubleshooting note for cache misses and dependency pinning.

## References

- Bazel getting started: https://bazel.build/start
- Bazel build concepts: https://bazel.build/concepts/build-ref
- Nix learning resources: https://nixos.org/learn/
- nix.dev: https://nix.dev/
- Curated primary sources: [docs/learning-resources.md](docs/learning-resources.md)
