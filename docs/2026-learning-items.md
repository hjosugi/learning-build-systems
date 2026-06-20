# 2026 Learning Items: Build Systems and Environments

Last verified: 2026-06-20

## Must Learn

### Build system fundamentals

- dependency graph
- target
- package
- workspace
- cache
- hermetic build
- reproducible environment
- local vs CI parity

Outcome:

- Explain what a build tool owns and what it should not own.
- Compare language-native tools with Bazel and Nix.

### Bazel

Bazel learning focus:

- Bazelisk
- MODULE.bazel / bzlmod basics
- BUILD files
- labels
- targets
- dependencies
- visibility
- hermeticity
- test targets
- remote cache concepts

Projects:

- `examples/bazel-java`: small Java library + test
- `examples/bazel-go`: small Go command + test
- `examples/bazel-typescript`: TypeScript build/test experiment
- `examples/bazel-python`: Python package/test experiment
- `examples/polyglot-bazel-nix`: one tiny multi-language build

Definition of done:

- `bazel build //...` documented
- `bazel test //...` documented
- README explains why Bazel is or is not worth it for the sample

### Nix

Nix learning focus:

- installing Nix
- ad hoc shells
- declarative shells
- flakes
- pinning nixpkgs
- devShells
- language-specific environments
- binary cache concepts
- CI with Nix

Projects:

- `examples/nix-devshell-node`: Node + pnpm environment
- `examples/nix-devshell-python`: Python + uv environment
- `examples/nix-devshell-java`: Java + Maven environment
- `templates/devshells`: reusable dev shell snippets

Definition of done:

- `nix develop` documented
- pinned input strategy documented
- README explains what is provided by Nix vs the language package manager

### Language-native build tools

Focus:

- Maven wrapper
- Gradle wrapper
- pnpm workspaces
- uv
- Go modules
- Make / just / task as command runners

Projects:

- comparison notes in `docs/build-tool-comparison.md`
- command-runner examples in `examples/command-runners`

Definition of done:

- Can explain when language-native tools are enough.
- Can explain when Bazel or Nix adds value.

### CI integration

Focus:

- GitHub Actions with Bazel
- GitHub Actions with Nix
- dependency caching
- build artifacts
- matrix builds
- local/CI parity

Projects:

- `templates/github-actions/bazel.yml`
- `templates/github-actions/nix.yml`
- `templates/github-actions/polyglot.yml`

Definition of done:

- Every template has a short explanation.
- Every template says what cache is safe to use.

## Tradeoff Questions

Use these before adopting a tool:

- Is this repo multi-language enough to need a graph-level build system?
- Do we need reproducible developer environments?
- Do CI and local builds currently diverge?
- Is setup time hurting learning more than helping?
- Can language-native tools solve this with less machinery?
- Will future contributors understand this setup?

## Repository Assignment

| Topic | Put it here? |
| --- | --- |
| Bazel examples | yes |
| Nix dev shells | yes |
| pnpm workspace basics | yes, as comparison |
| Maven/Gradle wrapper notes | yes, as comparison |
| Docker/Kubernetes deploy examples | no, use `learning-platform-engineering` |
| app-specific build scripts | no, keep in app repo |

