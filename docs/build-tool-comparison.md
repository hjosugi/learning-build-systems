# Build Tool Comparison

Last verified: 2026-06-20

## Purpose

This document compares build and environment tools by what they own.

## Comparison Matrix

| Tool | Owns | Good for | Watch out for |
| --- | --- | --- | --- |
| Bazel | build graph, targets, cache, tests | large or multi-language repos, repeatable builds | setup cost, rule complexity |
| Nix | packages, dev environments, system inputs | reproducible shells, pinned tools, CI parity | learning curve, platform differences |
| pnpm | JavaScript dependencies and workspaces | frontend/Node projects | does not define system dependencies |
| uv | Python env/dependency workflow | Python apps, scripts, tools | Python-focused only |
| Maven | Java dependency/build lifecycle | standard Java/Spring projects | less ideal for polyglot builds |
| Gradle | flexible JVM builds | Kotlin/Java, custom build logic | custom logic can become opaque |
| Go modules | Go dependency/build flow | Go projects | Go-focused only |
| Make/just/task | command orchestration | common commands and wrappers | not a dependency model by itself |

## Rule of Thumb

- Start with the language-native tool.
- Add Nix when environment reproducibility matters.
- Add Bazel when the build graph, cache, and polyglot scale justify the setup.
- Use command runners to make common commands discoverable, not to hide important build logic.

