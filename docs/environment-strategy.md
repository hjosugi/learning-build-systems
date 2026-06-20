# Environment Strategy

Last verified: 2026-06-20

## Layers

1. System tools: JDK, Node, Python, Go, Bazel, Nix
2. Language package manager: pnpm, uv, Maven, Gradle, Go modules
3. Build graph: Bazel or language-native build
4. Local services: databases, mail servers, queues
5. CI: same commands as local where possible

## Strategy

- Keep app repos simple until complexity appears.
- Use Nix to pin developer tools when "works on my machine" becomes a problem.
- Use Bazel when multiple languages and shared build/test caching matter.
- Keep Docker/Compose for services, not as the only way to run language tooling.
- Document the shortest path first, then the reproducible path.

