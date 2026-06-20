# Troubleshooting

Last verified: 2026-06-20

## Bazel

- If a target cannot see a dependency, check labels and visibility.
- If local state affects a build, check hermeticity assumptions.
- If builds are slow, inspect cache behavior before adding more tooling.

## Nix

- If `nix develop` gives a different result across machines, check pinned inputs.
- If a package is missing, decide whether it belongs in Nix or the language package manager.
- If a shell is too heavy, split base tools from optional tools.

## CI

- If CI differs from local, write down the exact command mismatch.
- Cache only directories that are safe and deterministic enough for the tool.
- Prefer one obvious build command over many hidden scripts.

