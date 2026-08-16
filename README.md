# TgDesktop Multi-Account Builder

Build custom Telegram Desktop with support for multiple accounts on Ubuntu 18/20+.

This script automates:
- Installing Docker prerequisites
- Cloning Telegram Desktop source (with full history)
- Modifying `kMaxAccounts` constant to enable N concurrent accounts
- Building Telegram Desktop in a Docker container using CentOS environment

## Prerequisites

- **OS**: Ubuntu 18.04 LTS, 20.04 LTS, or similar Debian-based distribution
- **Docker**: Automatically installed by the script (or install manually with `sudo apt install docker-ce`)
- **Git**: For cloning Telegram Desktop source
- **Telegram API credentials**: Get your API ID and hash from https://my.telegram.org/auth/login

## Installation

```bash
git clone https://github.com/LightYagami28/TgDesktop-multi-account.git
cd TgDesktop-multi-account
```

## Usage

```bash
python3 telegram_maker_multi.py
```

The script will guide you through the following steps interactively:

1. **Install Docker** (optional, only if not already installed)
   ```
   Installare requisiti Docker? [Y/n]: Y
   ```

2. **Download Telegram Desktop source** (or skip if you already have it)
   ```
   Scaricare Telegram Desktop source? [Y/n]: Y
   ```

3. **Modify account limit** (optional)
   ```
   Sostituire il numero massimo di account? [Y/n]: Y
   Quanti account vuoi avere al massimo?: 5
   ```

4. **Build with Docker**
   ```
   Usare Docker e buildare il source? [Y/n]: Y
   Inserisci il tuo API ID: 123456
   Inserisci il tuo API hash: abc123def456...
   Continuare con la build? [Y/n]: Y
   ```

## Build Time

The build process typically takes **30-60 minutes** depending on your system hardware and internet speed. The script will display progress as it builds.

## Output

After successful build, the compiled Telegram Desktop will be available in:
```
tdesktop/out/Release/
```

Look for the `Telegram` executable or `appimage` file.

## Development & Testing

Run the test suite to verify input validation and security:

```bash
python3 -m pytest test_telegram_maker.py -v
```

All 20 tests should pass ✓

## Security

This script has been refactored to prevent security vulnerabilities:

- ✅ No shell injection (uses `subprocess.run()` with argument lists)
- ✅ Input validation (API ID/hash, account count)
- ✅ Error handling with clear user feedback
- ✅ Comprehensive test coverage

See [SECURITY.md](SECURITY.md) for details.

## Development Notes

See [CLAUDE.md](CLAUDE.md) for development guidelines, coding standards, and troubleshooting.

## Troubleshooting

### Build fails with "permission denied"
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and log back in, or use:
newgrp docker
```

### Build fails with "Docker daemon not running"
```bash
sudo systemctl start docker
```

### Git clone times out
- Check your internet connection
- Try cloning with SSH instead of HTTPS
- Increase timeout: `git config --global http.lowSpeedTime 9000`

### Docker build is very slow
- This is normal! The first build compiles everything from source
- Subsequent builds will be faster (Docker layer caching)
- Consider building on a system with more CPU cores

## License

Apache License 2.0 - See [LICENSE](LICENSE) file

## Contributing

Improvements are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with: `python3 -m pytest test_telegram_maker.py -v`
5. Submit a pull request

## References

- [Telegram Desktop GitHub](https://github.com/telegramdesktop/tdesktop)
- [Telegram API Documentation](https://core.telegram.org/)
- [Docker Documentation](https://docs.docker.com/)
