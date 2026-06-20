# Learning Build Systems

Build tools and reproducible development environment experiments with Bazel, Nix, language-native build tools, and CI integration.

Last verified: 2026-06-20

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

## References

- Bazel getting started: https://bazel.build/start
- Bazel build concepts: https://bazel.build/concepts/build-ref
- Nix learning resources: https://nixos.org/learn/
- nix.dev: https://nix.dev/
