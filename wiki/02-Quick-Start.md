# Quick Start

## Interactive Mode

Simplest way to get started:

```bash
python3 telegram_maker_multi.py
```

The script will prompt you for:
1. How many concurrent accounts you want (voipn)
2. Your Telegram API ID
3. Your Telegram API hash
4. Whether to install Docker (if needed)
5. Whether to download Telegram source
6. Whether to start the build

## Programmatic Mode

For automation:

```bash
python3 telegram_maker_multi.py \
  --voip-count 10 \
  --api-id YOUR_API_ID \
  --api-hash YOUR_API_HASH \
  --log-dir ./custom_logs
```

## Output

The compiled binary is located at:
```
telegram_output/Telegram
```

## First Build (10-30 minutes)

- Downloads Telegram Desktop source (~500MB)
- Builds Docker image (~1.38GB)
- Compiles Telegram with your settings

Subsequent builds are much faster (~5-10 min) due to Docker caching.

## Troubleshooting

See [Troubleshooting](06-Troubleshooting.md) for common issues.
