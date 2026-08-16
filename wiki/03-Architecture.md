# Architecture

## System Flow

```
User Input
    ↓
Input Validation (security)
    ↓
Telegram Source Download (git clone)
    ↓
Modify kMaxAccounts (regex pattern)
    ↓
Build Docker Image (CentOS Stream 9)
    ↓
Run Docker Build (subprocess, memory limits)
    ↓
Verify Binary Output
    ↓
Copy to Output Directory
```

## Docker Environment

**Image:** CentOS Stream 9 (active support)

**Base Packages:**
- GCC 11 (compiler)
- CMake (build system)
- Qt5 (UI framework)
- OpenSSL (cryptography)
- Python3 (scripting)

**Security:**
- Non-root user (builder)
- Memory limits: 4GB default
- CPU limits: auto-detected
- Health checks enabled

## Key Functions

| Function | Purpose |
|----------|---------|
| `setup_logging()` | Initialize logging with path traversal protection |
| `validate_*()` | Input validation (voip_count, api_id, api_hash) |
| `modify_max_accounts()` | Update kMaxAccounts using regex |
| `build_docker_image()` | Create Docker image with caching |
| `run_build()` | Execute Docker build with resource limits |
| `clone_telegram_source()` | Git clone Telegram Desktop repo |
| `verify_build_output()` | Validate binary and copy to output |

## Security Checks

1. **Shell Injection Prevention** — `subprocess.run()` with argument lists
2. **Path Traversal Protection** — `Path.resolve()` + `relative_to()` validation
3. **Input Validation** — All user inputs checked before use
4. **Resource Isolation** — Docker memory/CPU limits
5. **Audit Trail** — Comprehensive logging with timestamps
