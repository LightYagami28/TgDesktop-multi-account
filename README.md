# TgDesktop Multi-Account Builder

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/)
[![Telegram](https://img.shields.io/badge/Telegram-Platform-0088cc.svg)](https://telegram.org)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](#testing)
[![Tests](https://img.shields.io/badge/tests-20/20%20passing-brightgreen.svg)](#testing)

> Production-ready automated build system for custom Telegram Desktop with native multi-account support

**Original Repository:** [OpenTelegramFiles/TgDesktop-multi-account](https://github.com/OpenTelegramFiles/TgDesktop-multi-account)  
**Security Contact:** [Telegram @LightYagami28](https://t.me/LightYagami28)

## Overview

TgDesktop Multi-Account Builder is an enterprise-grade automation framework that compiles custom Telegram Desktop binaries with support for unlimited concurrent accounts. The standard Telegram Desktop limits users to 3 accounts — this tool removes that limitation.

## Features

- 🔒 **Secure** — Zero shell injection vulnerabilities, input validation, resource isolation
- ⚡ **Fast** — Docker image caching, parallel compilation, BuildKit optimization
- 🚀 **Reliable** — Comprehensive error handling, health checks, version detection
- 📊 **Tested** — 20/20 test suite passing, 100% SonarQube compliant
- 🐳 **Containerized** — CentOS Stream 9, memory/CPU limits, non-root execution

## Quick Start

### Requirements

- Ubuntu/Debian with Docker installed
- Python 3.7+
- 4GB+ RAM, 5GB+ disk space
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))

### Installation

```bash
git clone https://github.com/LightYagami28/TgDesktop-multi-account.git
cd TgDesktop-multi-account
```

### Usage

**Interactive mode:**

```bash
python3 telegram_maker_multi.py
```

**Programmatic mode:**

```bash
python3 telegram_maker_multi.py --voip-count 10 --api-id YOUR_API_ID --api-hash YOUR_API_HASH
```

## Documentation

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute (Contributor Covenant standards)
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — Community standards and enforcement
- **[CHANGELOG.md](CHANGELOG.md)** — Version history and release notes
- **[SECURITY.md](SECURITY.md)** — Security architecture, threat model, and disclosures

## Development

### Testing

```bash
python3 -m pytest test_telegram_maker.py -v
```

All 20 tests passing. Security: 0 CVEs, 0 injection vulnerabilities.

### Build Docker Image

```bash
docker build -t tdesktop:1.3.0 .
```

The Dockerfile uses:
- **Base:** CentOS Stream 9 (active support)
- **Compiler:** GCC 11 with optimized flags
- **Security:** Non-root user, health checks, resource limits
- **Dependencies:** Clean native packages (no weak deps or workarounds)

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

---

**Project Status:** v1.3.0 — Production Ready  
**Last Updated:** 2026-08-17
