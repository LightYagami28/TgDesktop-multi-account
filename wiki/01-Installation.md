# Installation Guide

## System Requirements

### Minimum
- OS: Ubuntu 18.04 LTS or later
- RAM: 4 GB (configurable)
- Disk: 5 GB free space
- CPU: 2 cores
- Python: 3.7+
- Docker: latest

### Recommended
- OS: Ubuntu 20.04 LTS
- RAM: 16 GB
- Disk: 20 GB SSD
- CPU: 8 cores
- Network: 10 Mbps+

## Prerequisites

```bash
sudo apt install -y python3 git curl
```

Telegram API credentials at [my.telegram.org](https://my.telegram.org)

## Setup

```bash
git clone https://github.com/LightYagami28/TgDesktop-multi-account.git
cd TgDesktop-multi-account
```

## Docker Setup

Docker will be installed automatically on first run if missing. For manual installation:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

## Verify Installation

```bash
python3 --version
docker --version
git --version
```

All should return version numbers.
