# security.md

## Shell Injection (Critical)

**Lines 22, 26**: User inputs (`voipn`, `apiid`, `apihash`) are concatenated directly into `os.system()` strings. A user entering `"; rm -rf /"` would execute arbitrary commands.

**Refactor all `os.system()` calls to `subprocess.run()`** with argument lists (no shell=True). Example:

```python
# Before (vulnerable)
os.system("sudo apt install docker-ce")

# After (safe)
subprocess.run(["sudo", "apt", "install", "docker-ce"], check=True)
```

For the build command (line 26), build the argument list programmatically:

```python
cmd = [
    "docker", "run", "--rm", "-it",
    "-v", f"{os.getcwd()}:/usr/src/tdesktop",
    "-e", "DEBUG=1",
    "tdesktop:centos_env",
    "/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh",
    f"-DTDESKTOP_API_ID={apiid}",
    f"-DTDESKTOP_API_HASH={apihash}",
    "-DDESKTOP_APP_USE_PACKAGED=OFF",
    "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF"
]
subprocess.run(cmd, check=True)
```

## Input Validation

**Line 17 (voipn)**: Must be a positive integer. Add validation:
```python
while True:
    voipn = input("quanti voip vuoi avere max?: ")
    if voipn.isdigit() and int(voipn) > 0:
        break
    print("Inserisci un numero positivo.")
```

**Lines 23-24 (API credentials)**: Must not be empty or contain special characters. Validate format:
```python
apiid = input("inserisci il tuo api id: ").strip()
if not apiid.isdigit():
    print("API ID deve essere un numero.")
    exit(1)
```

## Error Handling

All `subprocess.run()` calls should use `check=True` to raise an exception on non-zero exit codes. Wrap critical sections in try-except to provide user-friendly error messages.

## Secrets Management

Never log or print API credentials. If debug output is needed, redact them (e.g., `apiid[:3] + "***"`).
