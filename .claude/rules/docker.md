# docker.md

## Docker Build Process

The script builds a Docker image from the Telegram Desktop CentOS environment, then uses it to compile the modified source.

### Build Image Setup (Line 22)

```
docker build -t tdesktop:centos_env telegramdesktop/Telegram/build/docker/centos_env/
```

**Quirks**:
- The `telegramdesktop/` path is relative to the cloned source (line 11). This assumes `tdesktop/` exists in the current directory.
- Image is tagged as `tdesktop:centos_env` and reused for builds.
- CentOS environment provides specific versions of build tools (gcc, cmake, Qt) that match Telegram Desktop's requirements.

**Future improvement**: Consider building with `--no-cache` on first run, or making the image tag configurable.

## Docker Run Build (Line 26)

```
docker run --rm -it -v $PWD:/usr/src/tdesktop -e DEBUG=1 tdesktop:centos_env /usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh
```

**Flags**:
- `--rm`: Remove container after build (cleanup)
- `-it`: Interactive + TTY (for build output and prompts)
- `-v $PWD:/usr/src/tdesktop`: Mount current directory as source volume
- `-e DEBUG=1`: Enable debug output during build
- Build script path is hardcoded; assumes standard Telegram Desktop structure

**API credentials passed as**:
- `-DTDESKTOP_API_ID=<apiid>`
- `-DTDESKTOP_API_HASH=<apihash>`
- These are CMake flags, not environment variables; passed directly to build.sh

**Other flags** (hardcoded):
- `-DDESKTOP_APP_USE_PACKAGED=OFF`: Link system libraries (vs vendored)
- `-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF`: Enable crash reporting

## Troubleshooting

- **Build fails silently**: Check return code (subprocess refactor needed). Docker output goes to stdout; examine it carefully.
- **Permission denied errors**: May need `sudo` or user added to docker group (`sudo usermod -aG docker $USER`).
- **Volume mount issues**: `$PWD` expansion happens in shell. When refactoring to subprocess, use `os.getcwd()` explicitly.
- **API credentials rejected**: Verify credentials are valid and don't contain special characters (see security.md).

## Future Improvements

- Make image tag configurable (allow different build environments)
- Add build output logging to a file
- Support parallel builds with different account counts
- Cache intermediate build layers more aggressively
