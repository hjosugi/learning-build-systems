# Nix Devshell Lab

Minimal Nix flake for learning pinned development shells.

## Enter The Shell When Nix Is Installed

```bash
cd projects/nix-devshell-lab
nix develop
```

Inside the shell:

```bash
python --version
node --version
```

## Environment Check

```bash
python3 projects/nix-devshell-lab/check_nix.py
```

