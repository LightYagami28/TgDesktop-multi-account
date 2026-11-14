"""Opzioni di build, percorsi e funzioni di supporto pure del builder."""
import logging
from dataclasses import dataclass
from pathlib import Path

from validation import validate_api_hash, validate_api_id

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildOptions:
    """Risorse del container e flag CMake aggiuntivi della build."""

    memory_limit: str = "4g"
    cpus: str = "2"
    extra_flags: str = ""


DEFAULT_OPTIONS = BuildOptions()

TDESKTOP_REPO = "https://github.com/telegramdesktop/tdesktop.git"

APT_PREREQUISITES = ["ca-certificates", "curl"]
DOCKER_KEYRING = "/etc/apt/keyrings/docker.asc"
DOCKER_SOURCE_FILE = "/etc/apt/sources.list.d/docker.list"


def _confined_log_path(log_dir):
    """Percorso del log, confinato nella cartella corrente."""
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


def docker_apt_source(codename, arch):
    """Riga del repository Docker, firmata dal keyring dedicato."""
    return (
        f"deb [arch={arch} signed-by={DOCKER_KEYRING}] "
        f"https://download.docker.com/linux/ubuntu {codename} stable\n"
    )


def _asked_value(prompt, default):
    """Chiede un valore; Invio restituisce quello proposto."""
    value = input(prompt)
    return value if value else default


def _flag_preview(extra_flags):
    """Testo mostrato come default dei flag CMake nel prompt."""
    return extra_flags if extra_flags else "vuoto"


def _validated_credentials(apiid, apihash):
    """Credenziali validate, oppure None dopo aver loggato l'errore."""
    try:
        return validate_api_id(apiid), validate_api_hash(apihash)
    except ValueError:
        logger.exception("Credenziali non valide")
        return None


def _cmake_flags(apiid, apihash, cpus, extra_flags):
    """Flag CMake della build, con credenziali e parallelismo."""
    return [
        f"-DTDESKTOP_API_ID={apiid}",
        f"-DTDESKTOP_API_HASH={apihash}",
        "-DDESKTOP_APP_USE_PACKAGED=OFF",
        "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF",
        f"-DCMAKE_BUILD_PARALLEL_LEVEL={cpus}",
        *extra_flags.split(),
    ]


def _docker_run_command(cwd, cpus, memory_limit, cmake_flags):
    """Comando docker run per la build nel container."""
    return [
        "docker", "run", "--rm", "-i",
        "-m", memory_limit,
        "--cpus", str(cpus),
        "-v", f"{cwd}:/usr/src/tdesktop",
        "-e", "DEBUG=1",
        "-e", f"MAKEFLAGS=-j{cpus}",
        "tdesktop:centos_env",
        "/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh",
        *cmake_flags,
    ]


def _log_build_config(apiid, apihash, memory_limit, cpus):
    """Logga la configurazione, con le credenziali mascherate."""
    cpus_requested, cpus_available = cpus
    logger.info("Configurazione build:")
    logger.info(
        "  Memory limit: %s, CPUs: %s/%s", memory_limit, cpus_requested, cpus_available
    )
    logger.info("  API ID: %s***, API Hash: %s***...", apiid[:3], apihash[:6])
    logger.info("Avvio della build in Docker...")
