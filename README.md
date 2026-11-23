# TgDesktop Multi-Account Builder

[![Tests](https://github.com/LightYagami28/TgDesktop-multi-account/actions/workflows/tests.yml/badge.svg)](https://github.com/LightYagami28/TgDesktop-multi-account/actions/workflows/tests.yml)
[![CodeQL](https://github.com/LightYagami28/TgDesktop-multi-account/actions/workflows/codeql-analysis.yml/badge.svg)](https://github.com/LightYagami28/TgDesktop-multi-account/actions/workflows/codeql-analysis.yml)
[![Python](https://img.shields.io/badge/Python-3.13%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Tests Passing](https://img.shields.io/badge/tests-103%2F103%20passing-brightgreen)](docs/TESTING.md)
[![Docker](https://img.shields.io/badge/Docker-build%20ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Interactive Python script that builds a custom [Telegram
Desktop](https://github.com/telegramdesktop/tdesktop) inside a Docker container,
with a configurable maximum number of simultaneous accounts (`kMaxAccounts`).

Original repository:
[OpenTelegramFiles/TgDesktop-multi-account](https://github.com/OpenTelegramFiles/TgDesktop-multi-account).

## What it does

1. Optionally installs Docker on Ubuntu/Debian.
2. Clones the Telegram Desktop source (`tdesktop/`) or patches `kMaxAccounts` in
   an existing checkout.
3. Builds the upstream `centos_env` Docker image.
4. Runs the compile inside the container and copies the binary to
   `telegram_output/Telegram`.

Prompts and log messages are in Italian. Details in [SPEC.md](SPEC.md).

## Requirements

- Linux (Ubuntu/Debian for the automatic Docker install; any distro with Docker
  works otherwise)
- Python 3.13 or newer (CI covers 3.13, 3.14, 3.15). The script uses only the
  standard library: no `pip install` needed
- Docker, git, `sudo` (only for the optional Docker install)
- At least 4 GB RAM and 5 GB disk, plus time: a full build takes a long while
- Telegram API credentials (`api_id`, `api_hash`) from
  [my.telegram.org](https://my.telegram.org)

## Installation

```bash
git clone https://github.com/LightYagami28/TgDesktop-multi-account.git
cd TgDesktop-multi-account
```

## Usage

```bash
python3 telegram_maker_multi.py [options]
```

Answer the prompts (`[Y/n]`: Enter accepts the default). When asked, type the
API ID and API hash.

| Option | Default | Meaning |
| ------ | ------- | ------- |
| `--force-rebuild` | off | Rebuild the Docker image even if it exists |
| `--memory` | `4g` | Container memory limit |
| `--cpus` | `2` | CPU count (capped to the available ones) |
| `--cmake-flags` | empty | Extra CMake flags, space separated |
| `--log-dir` | `tdesktop` | Log directory (must stay inside the current directory) |

Output: `telegram_output/Telegram`; logs in
`<log-dir>/telegram_build_<timestamp>.log`.

## Configuration

The script reads **no environment variables** and needs no `.env` file.
Credentials are asked interactively and never written to disk; only a masked
prefix appears in the logs. Everything else is configured through the options
above.

## Tests and checks

```bash
python3 -m unittest -v test_telegram_maker.py
python3 -m py_compile telegram_maker_multi.py build_helpers.py command_runner.py source_patch.py validation.py
```

CI runs the same unit tests on Python 3.13, 3.14 and 3.15, plus Ruff, Bandit,
Mypy, pip-audit and SonarCloud (`.github/workflows/tests.yml`); CodeQL is in
`.github/workflows/codeql-analysis.yml`. GitHub Actions are pinned by commit SHA.

## Documentation

- [SPEC.md](SPEC.md): purpose, architecture, flows, stack, security, limits,
  roadmap
- [Architecture](ARCHITECTURE.md), [Roadmap](ROADMAP.md)
- [Testing](docs/TESTING.md), [Troubleshooting](docs/TROUBLESHOOTING.md)
- [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md),
  [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [CHANGELOG.md](CHANGELOG.md)
- [Wiki](https://github.com/LightYagami28/TgDesktop-multi-account/wiki)

## Security

Report vulnerabilities as described in [SECURITY.md](SECURITY.md) (Telegram:
[@LightYagami28](https://t.me/LightYagami28)).

## License

Apache License 2.0, see [LICENSE](LICENSE).
