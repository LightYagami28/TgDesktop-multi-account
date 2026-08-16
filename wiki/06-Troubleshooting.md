# Troubleshooting

## Build Fails Silently

**Symptom:** No error message, but binary not created.

**Solution:** Check Docker logs:
```bash
docker logs <container_id>
```

Verify Docker is running:
```bash
docker ps
docker images
```

## Permission Denied (Docker)

**Symptom:** `Got permission denied while trying to connect to Docker daemon`

**Solution:** Add user to docker group:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

Then re-run the script.

## Out of Disk Space

**Symptom:** Build fails with "No space left on device"

**Solution:** Check available space:
```bash
df -h
```

Required space:
- Source code: ~1.5GB
- Docker image: ~1.4GB
- Build artifacts: ~500MB
- Total: ~5GB

## API Credentials Invalid

**Symptom:** Build fails with API credential error.

**Solution:**
1. Verify credentials at [my.telegram.org](https://my.telegram.org)
2. Ensure no special characters in API hash
3. API ID should be numeric only

## Timeout During Download

**Symptom:** Git clone fails or hangs.

**Solution:**
```bash
rm -rf tdesktop
```

Retry with better network or try later.

## Docker Image Already Exists

**Symptom:** Script says image exists but doesn't work.

**Solution:** Force rebuild:
```bash
docker rmi tdesktop:centos_env
```

Then re-run script.

## Build Hangs

**Symptom:** Build runs but never completes.

**Solution:**
1. Check memory: `free -h` (needs 4GB+)
2. Kill hanging process: `docker kill <container_id>`
3. Check CPU usage: `top`

## Still Having Issues?

1. Check logs: `tail -f tdesktop/telegram_build_*.log`
2. Report at: [@LightYagami28](https://t.me/LightYagami28)
