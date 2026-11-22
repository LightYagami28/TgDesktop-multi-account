"""Build options, paths and pure helper functions for the Telegram Desktop builder."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from validation import validate_api_hash, validate_api_id

logger: logging.Logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildOptions:
    """Container resources and additional CMake flags for a build."""

    memory_limit: str = "4g"
    cpus: str = "2"
    extra_flags: str = ""


DEFAULT_OPTIONS: Final[BuildOptions] = BuildOptions()
TDESKTOP_REPO: Final[str] = "https://github.com/telegramdesktop/tdesktop.git"
APT_PREREQUISITES: Final[tuple[str, ...]] = ("ca-certificates", "curl")
DOCKER_KEYRING: Final[str] = "/etc/apt/keyrings/docker.asc"
DOCKER_SOURCE_FILE: Final[str] = "/etc/apt/sources.list.d/docker.list"


def _confined_log_path(log_dir: str) -> Path:
    """Resolve a log directory, confining it inside the current directory.

    Args:
        log_dir: User-supplied directory name.

    Returns:
        Absolute path inside the current working directory. Falls back to
        ``tdesktop`` when the input tries to escape it.
    """
    base_dir = Path.cwd()
    log_path = (base_dir / log_dir).resolve()
    try:
        log_path.relative_to(base_dir)
    except ValueError:
        logger.warning(
            "Log directory %s attempts path traversal. Using default 'tdesktop'",
            log_dir,
        )
        return base_dir / "tdesktop"
    return log_path


def docker_apt_source(codename: str, arch: str) -> str:
    """Build the signed Docker apt repository line.

    Args:
        codename: Ubuntu release codename.
        arch: Debian architecture reported by dpkg.

    Returns:
        A single ``deb`` line using the dedicated keyring.
    """
    return (
        f"deb [arch={arch} signed-by={DOCKER_KEYRING}] "
        f"https://download.docker.com/linux/ubuntu {codename} stable\n"
    )


def _asked_value(prompt: str, default: str) -> str:
    """Ask for a value, returning the proposed default on Enter.

    Args:
        prompt: Text shown to the user.
        default: Value used when the answer is empty.

    Returns:
        The answer or the default.
    """
    value = input(prompt)
    return value if value else default


def _flag_preview(extra_flags: str) -> str:
    """Return a readable preview of the extra CMake flags.

    Args:
        extra_flags: Raw flag string.

    Returns:
        The flags, or ``"vuoto"`` when none are configured.
    """
    return extra_flags if extra_flags else "vuoto"


def _validated_credentials(apiid: str, apihash: str) -> tuple[str, str] | None:
    """Validate API credentials, logging any error.

    Args:
        apiid: Raw API ID input.
        apihash: Raw API hash input.

    Returns:
        Validated credentials, or ``None`` when validation fails.
    """
    try:
        return validate_api_id(apiid), validate_api_hash(apihash)
    except ValueError:
        logger.exception("Credenziali non valide")
        return None


def _cmake_flags(apiid: str, apihash: str, cpus: int, extra_flags: str) -> list[str]:
    """Build the CMake flag list for the build.

    Args:
        apiid: Validated Telegram API ID.
        apihash: Validated Telegram API hash.
        cpus: Number of parallel build jobs.
        extra_flags: Space-separated additional flags (already validated).

    Returns:
        Argument list passed to the build script.
    """
    return [
        f"-DTDESKTOP_API_ID={apiid}",
        f"-DTDESKTOP_API_HASH={apihash}",
        "-DDESKTOP_APP_USE_PACKAGED=OFF",
        "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF",
        f"-DCMAKE_BUILD_PARALLEL_LEVEL={cpus}",
        *extra_flags.split(),
    ]


def _docker_run_command(
    cwd: str,
    cpus: int,
    memory_limit: str,
    cmake_flags: list[str],
) -> list[str]:
    """Build the docker run argument list.

    Args:
        cwd: Host directory mounted into the container.
        cpus: CPU limit for the container.
        memory_limit: Memory limit for the container.
        cmake_flags: Flags forwarded to the build script.

    Returns:
        Argument list for ``docker run`` (never a shell string).
    """
    return [
        "docker",
        "run",
        "--rm",
        "-i",
        "-m",
        memory_limit,
        "--cpus",
        str(cpus),
        "-v",
        f"{cwd}:/usr/src/tdesktop",
        "-e",
        "DEBUG=1",
        "-e",
        f"MAKEFLAGS=-j{cpus}",
        "tdesktop:centos_env",
        "/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh",
        *cmake_flags,
    ]


def _log_build_config(
    apiid: str,
    apihash: str,
    memory_limit: str,
    cpus: tuple[int, int],
) -> None:
    """Log the build configuration with credentials masked.

    Args:
        apiid: Validated API ID (only its prefix is logged).
        apihash: Validated API hash (only its prefix is logged).
        memory_limit: Container memory limit.
        cpus: Requested and available CPU counts.
    """
    cpus_requested, cpus_available = cpus
    logger.info("Configurazione build:")
    logger.info(
        "  Memory limit: %s, CPUs: %s/%s", memory_limit, cpus_requested, cpus_available
    )
    logger.info("  API ID: %s***, API Hash: %s***...", apiid[:3], apihash[:6])
    logger.info("Avvio della build in Docker...")
