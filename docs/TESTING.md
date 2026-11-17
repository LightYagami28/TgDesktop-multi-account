# Testing

The repository documents Python unit tests and static syntax validation. From the repository root on a system with Python 3 installed:

```sh
python3 -m unittest -v test_telegram_maker.py
python3 -m py_compile telegram_maker_multi.py build_helpers.py source_patch.py validation.py
```

A complete Docker build is a separate, resource-intensive integration check; use the prerequisites and instructions in the [README](../README.md). The CI workflow is the source of truth for automated checks.