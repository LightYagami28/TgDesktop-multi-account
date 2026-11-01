# SPEC

## Purpose

Automate building a custom Telegram Desktop with a user-chosen account limit, avoiding manual toolchain setup by using the upstream Docker build environment.

## Features

- Optional Docker installation (Ubuntu/Debian, via `apt`)
- Clone of `telegramdesktop/tdesktop` (recursive) or reuse of an existing `tdesktop/` directory
- Regex patch of `kMaxAccounts` in `tdesktop/Telegram/SourceFiles/main/main_domain.h`
- Build of the Docker image `tdesktop:centos_env` (reused unless `--force-rebuild`)
- Containerized compile with memory and CPU limits, extra CMake flags
- Output copied to `telegram_output/Telegram`; timestamped log file

## Architecture

Modules: `telegram_maker_multi.py`, `validation.py` (input checks, yes/no
prompts) and `source_patch.py` (kMaxAccounts patch). No third-party
dependencies. All external work goes through `subprocess.run` with argument
lists (no shell).

| Function | Role |
|----------|------|
| `main` | CLI parsing (`argparse`) and workflow orchestration |
| `ask_yes_no` | `[Y/n]` prompt, Enter selects the default |
| `validate_voip_count`, `validate_api_id`, `validate_api_hash` | Input validation |
| `install_dependencies` | Docker CE install through `sudo apt` |
| `clone_telegram_source` | Source acquisition |
| `modify_max_accounts` | kMaxAccounts patch (`source_patch.py`) |
| `build_docker_image`, `run_build` | Image build and containerized compile |
| `verify_build_output` | Checks and copies the binary |
| `setup_logging` | File + stdout logging, path traversal guard |

## Main flow

1. `main` sets up logging and prints system info.
2. Prompt: install Docker? -> `install_dependencies`.
3. `handle_source_download`: clone, or (if the source exists) optionally patch `kMaxAccounts`.
4. Prompt: build with Docker? -> `handle_docker_build`: image build, API ID/hash prompt, optional advanced options, `run_build`.
5. `run_build` runs `docker run` mounting the current directory at `/usr/src/tdesktop`, then `verify_build_output`.

## Data

No database. Files: `tdesktop/` (source, logs), `telegram_output/Telegram` (binary). No environment variables are read; `DEBUG=1` and `MAKEFLAGS` are passed to the container.

## Interfaces

- CLI options: see [README.md](README.md)
- External: `docker`, `git`, `sudo/apt`, `curl`, GitHub (`telegramdesktop/tdesktop`), Docker apt repository
- Dockerfile at the repo root: hardened CentOS Stream 9 build image (non-root user, JSON healthcheck)

## Stack

| Component | Version |
|-----------|---------|
| Python | 3.13, 3.14, 3.15 tested in CI (3.15.2 is the latest stable as of 2026-10-31) |
| Test runner | `unittest` (stdlib) |
| Base image | CentOS Stream 9 (`quay.io/centos/centos:stream9`) |
| `actions/checkout` | v7.0.1 (pinned by SHA) |
| `actions/setup-python` | v7.1.0 (pinned by SHA) |
| `github/codeql-action` | v4.39.1 (pinned by SHA) |

## Security

- No `shell=True`; argument lists only
- API ID/hash validated, never saved, masked in logs
- `--log-dir` is confined to the current directory
- Workflows: minimal permissions, `persist-credentials: false`, SHA-pinned actions, CodeQL weekly and on PR
- Policy and reporting: [SECURITY.md](SECURITY.md)

## Known limits

- Docker install targets Ubuntu/Debian with the Ubuntu Docker repository
  (keyring in `/etc/apt/keyrings`, codename from `/etc/os-release`)
- The Dockerfile uses Qt5 packages; moving to CentOS Stream 10 needs a check of package availability
- `kMaxAccounts` patch depends on the upstream source format
- The clone has no pinned tag: the build tracks upstream `master`
- Prompts and logs only in Italian; Linux only (`os.uname`)
- The actual compile is not covered by tests or CI (too heavy); tests cover validation and helpers

## Roadmap

- Option to pin the upstream tag/commit
- Non-interactive mode (flags for API ID/hash via stdin or file)
- English translation of messages
