# Native Build Runner

A tiny build-system exercise that models targets without requiring Bazel, Nix, or Make.

## Run

```bash
python3 projects/native-build-runner/build.py all
```

## Targets

```bash
python3 projects/native-build-runner/build.py clean
python3 projects/native-build-runner/build.py build
python3 projects/native-build-runner/build.py test
```

## Exercise

Port the same target graph to Make, Bazel, and Nix. Keep the commands and outputs comparable.

