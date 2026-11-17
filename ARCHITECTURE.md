# Architecture

This repository builds a Telegram Desktop variant with multiple-account support. The documented workflow is a source patch and validation pipeline around an upstream `tdesktop/` checkout, followed by a Linux build in Docker and artifacts under `telegram_output/Telegram`.

## Main components

- `telegram_maker_multi.py` coordinates the build workflow and user interaction.
- `build_helpers.py` contains build support routines.
- `source_patch.py` applies source changes to the upstream checkout.
- `validation.py` checks inputs and generated state.
- `test_telegram_maker.py` contains the Python unit tests.

## Boundaries

The repository automates the build; it does not provide a hosted Telegram service. Build output and upstream source are generated inputs/outputs, not documentation sources. See `SPEC.md` for design decisions and status notes.