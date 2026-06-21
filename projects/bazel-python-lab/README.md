# Bazel Python Lab

Minimal Bazel project for learning `MODULE.bazel`, `BUILD.bazel`, labels, and test targets.

## Run When Bazel Or Bazelisk Is Installed

```bash
cd projects/bazel-python-lab
bazel test //...
```

## Environment Check

```bash
python3 projects/bazel-python-lab/check_bazel.py
```

## What To Learn

- how labels such as `//:greeting_test` point to targets
- why source files and tests are declared explicitly
- how this differs from `python3 greeting_test.py`

