"""Build Telegram Desktop with a custom account limit inside Docker."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from build_helpers import (
    APT_PREREQUISITES,
    DEFAULT_OPTIONS,
    DOCKER_KEYRING,
    DOCKER_SOURCE_FILE,
    TDESKTOP_REPO,
    BuildOptions,
    _asked_value,
    _cmake_flags,
    _confined_log_path,
    _docker_run_command,
    _flag_preview,
    _log_build_config,
    _validated_credentials,
    docker_apt_source,
)
from command_runner import (
    DEVNULL,
    CommandError,
    CompletedCommand,
    run as run_process,
)
from source_patch import modify_max_accounts
from validation import ask_yes_no

logger: logging.Logger = logging.getLogger(__name__)

# Solo questi eseguibili possono essere avviati: gli input dell'utente sono
# convalidati dai moduli dedicati e restano sempre argomenti separati.
ALLOWED_COMMANDS = frozenset(
    {
        "apt",
        "chmod",
        "curl",
        "docker",
        "dpkg",
        "git",
        "install",
        "sudo",
        "systemctl",
        "tee",
    }
)

# Solo queste opzioni raggiungono il runner di processi. Qualsiasi altra
# opzione (compresa una richiesta di shell) viene rifiutata prima dell'esecuzione.
ALLOWED_OPTIONS = frozenset(
    {"capture_output", "env", "input", "stderr", "stdout", "text", "timeout"}
)


def run_command(cmd: list[str], **kwargs: Any) -> CompletedCommand:
    """Run a whitelisted command by absolute path, never through a shell.

    User-supplied values are validated before they reach an argument list,
    so no string is ever interpreted by a shell.

    Args:
        cmd: Whitelisted executable name followed by its separate arguments.
        **kwargs: Extra keyword arguments forwarded to the process runner.

    Returns:
        The completed command.

    Raises:
        FileNotFoundError: When the executable is not allowed or cannot be resolved.
        ValueError: When an option outside ``ALLOWED_OPTIONS`` is requested.
        CommandError: When the command exits non-zero.
    """
    if not cmd or cmd[0] not in ALLOWED_COMMANDS:
        raise FileNotFoundError(f"Comando non consentito: {cmd[0] if cmd else ''}")
    unsupported = set(kwargs) - ALLOWED_OPTIONS
    if unsupported:
        raise ValueError(f"opzioni non consentite: {sorted(unsupported)}")
    executable = shutil.which(cmd[0])
    if executable is None or not PurePosixPath(executable).is_absolute():
        raise FileNotFoundError(f"Comando non trovato: {cmd[0]}")
    argv = [executable, *cmd[1:]]
    return run_process(argv, check=True, **kwargs)


def setup_logging(log_dir: str = "tdesktop") -> str:
    """Configure file and console logging, returning the log file path.

    Args:
        log_dir: Directory name, confined inside the current directory.

    Returns:
        Path of the newly created log file.
    """
    log_path = _confined_log_path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    log_file = str(log_path / f"telegram_build_{datetime.now():%Y%m%d_%H%M%S}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_file


def docker_image_exists(image_name: str) -> bool:
    """Check whether a Docker image exists locally.

    Args:
        image_name: Image tag to inspect.

    Returns:
        ``True`` when the image has an ID, ``False`` on error or absence.
    """
    try:
        result = run_command(
            ["docker", "images", "-q", image_name], capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except CommandError:
        logger.exception("Failed to check Docker images")
        return False


def get_docker_image_info(image_name: str) -> dict[str, Any] | None:
    """Read Docker metadata for an image.

    Args:
        image_name: Image tag to inspect.

    Returns:
        First metadata object, or ``None`` on error or malformed output.
    """
    try:
        result = run_command(
            ["docker", "inspect", image_name], capture_output=True, text=True
        )
        return json.loads(result.stdout)[0]
    except (CommandError, json.JSONDecodeError, IndexError):
        return None


def get_system_cpus() -> int:
    """Return the number of usable CPUs.

    Returns:
        Affinity size when available, otherwise the OS count, or 2 as fallback.
    """
    try:
        if hasattr(os, "sched_getaffinity"):
            return len(os.sched_getaffinity(0))
        return os.cpu_count() or 2
    except (AttributeError, OSError):
        return 2


def _add_docker_key() -> None:
    """Download Docker's GPG key into its dedicated keyring.

    Returns:
        None.

    Raises:
        CommandError: When any installation step fails.
    """
    key = run_command(
        ["curl", "-fsSL", "https://download.docker.com/linux/ubuntu/gpg"],
        capture_output=True,
        text=True,
    )
    run_command(["sudo", "install", "-d", "-m", "0755", "/etc/apt/keyrings"])
    run_command(
        ["sudo", "tee", DOCKER_KEYRING],
        input=key.stdout,
        text=True,
        stdout=DEVNULL,
    )
    run_command(["sudo", "chmod", "a+r", DOCKER_KEYRING])


def _add_docker_repo() -> None:
    """Write the Docker apt repository for the current release and architecture.

    Returns:
        None.

    Raises:
        CommandError: When dpkg or tee fails.
    """
    codename = platform.freedesktop_os_release().get("VERSION_CODENAME", "focal")
    arch = run_command(
        ["dpkg", "--print-architecture"], capture_output=True, text=True
    ).stdout.strip()
    run_command(
        ["sudo", "tee", DOCKER_SOURCE_FILE],
        input=docker_apt_source(codename, arch),
        text=True,
        stdout=DEVNULL,
    )


def _install_docker_ce() -> None:
    """Install Docker CE and start its daemon.

    Returns:
        None.

    Raises:
        CommandError: When apt or systemctl fails.
    """
    logger.info("  • Installazione di Docker CE e avvio del daemon...")
    run_command(["sudo", "apt", "update"])
    run_command(["sudo", "apt", "install", "-y", "docker-ce"])
    run_command(["sudo", "systemctl", "start", "docker"])
    run_command(["sudo", "systemctl", "status", "docker"])


def install_dependencies() -> None:
    """Install the Docker prerequisites on Ubuntu/Debian.

    Returns:
        None.

    Raises:
        SystemExit: With code 1 when an installation command fails.
    """
    logger.info("Installazione dei prerequisiti Docker in corso...")
    try:
        logger.info("  • Installazione dipendenze base...")
        run_command(["sudo", "apt", "install", "-y", *APT_PREREQUISITES])
        logger.info("  ✓ Dipendenze base installate")

        logger.info("  • Aggiunta chiave GPG e repository di Docker...")
        _add_docker_key()
        _add_docker_repo()
        logger.info("  ✓ Chiave e repository aggiunti")

        _install_docker_ce()
        logger.info("✓ Docker installato e avviato")
    except CommandError as exc:
        logger.exception("✗ Errore installazione (exit code %s)", exc.returncode)
        sys.exit(1)


def clone_telegram_source() -> bool:
    """Clone the Telegram Desktop source tree when missing.

    Returns:
        ``True`` when the source is available, ``False`` when cloning fails.
    """
    if os.path.isdir("tdesktop"):
        logger.warning("La directory tdesktop esiste già. Saltando il clone...")
        return True

    logger.info("Clonazione source code di Telegram Desktop in corso (alcuni minuti)...")
    try:
        run_command(["git", "clone", "--recursive", TDESKTOP_REPO])
        logger.info("✓ Source code clonato con successo")
        return True
    except CommandError as exc:
        logger.exception("✗ Errore clone (exit code %s)", exc.returncode)
        return False


def verify_build_output(binary_path: str) -> bool:
    """Verify the compiled binary and copy it to ``telegram_output``.

    Args:
        binary_path: Expected path of the compiled Telegram binary.

    Returns:
        ``True`` when the binary exists; copying is best-effort.
    """
    if not os.path.isfile(binary_path):
        logger.warning("Binary non trovato: %s", binary_path)
        return False

    file_size = os.path.getsize(binary_path) / (1024**2)
    mod_time = datetime.fromtimestamp(os.path.getmtime(binary_path))

    logger.info("✓ Binary trovato: %s", binary_path)
    logger.info("  Dimensione: %.2f MB", file_size)
    logger.info("  Modificato: %s", mod_time)

    output_dir = "telegram_output"
    Path(output_dir).mkdir(exist_ok=True)
    output_path = os.path.join(output_dir, "Telegram")

    try:
        shutil.copy2(binary_path, output_path)
        logger.info("✓ Binary copiato in: %s", output_path)
    except OSError as exc:
        logger.warning("Impossibile copiare binary: %s", exc)
    return True


def _log_image_size(image_info: dict[str, Any], label: str) -> None:
    """Log a Docker image size in gigabytes.

    Args:
        image_info: Metadata returned by ``docker inspect``.
        label: Description printed before the value.
    """
    size = image_info.get("Size", 0) / (1024**3)
    logger.info("  %s: %.2fGB", label, size)


def _report_existing_image(image_name: str) -> bool:
    """Report an existing image, or indicate that it must be built.

    Args:
        image_name: Image tag to inspect.

    Returns:
        ``True`` when the image is present and readable.
    """
    if not docker_image_exists(image_name):
        return False
    image_info = get_docker_image_info(image_name)
    if not image_info:
        return False
    logger.info("✓ Immagine Docker esiste già: %s", image_name)
    logger.info("  Creata: %s", image_info.get("Created", "unknown"))
    _log_image_size(image_info, "Dimensione")
    return True


def _docker_build(image_name: str, dockerfile_path: str) -> None:
    """Build a Docker image from the given context.

    Args:
        image_name: Tag assigned to the new image.
        dockerfile_path: Build context path.

    Returns:
        None.

    Raises:
        CommandError: When the build fails.
    """
    run_command(
        [
            "docker", "build",
            "--progress", "plain",
            "--build-arg", "BUILDKIT_INLINE_CACHE=1",
            "-t", image_name,
            dockerfile_path,
        ]
    )


def _build_image_and_report(image_name: str, dockerfile_path: str) -> bool:
    """Build the image and log its final size.

    Args:
        image_name: Tag assigned to the new image.
        dockerfile_path: Build context path.

    Returns:
        ``True`` on success, ``False`` when the build fails.
    """
    try:
        _docker_build(image_name, dockerfile_path)
    except CommandError as exc:
        logger.exception("✗ Errore build Docker (exit code %s)", exc.returncode)
        return False
    logger.info("✓ Immagine Docker creata con successo")

    image_info = get_docker_image_info(image_name)
    if image_info:
        _log_image_size(image_info, "Dimensione finale")
    return True


def build_docker_image(force_rebuild: bool = False) -> bool:
    """Build the Docker build image when missing or explicitly requested.

    Args:
        force_rebuild: Rebuild even when a local image already exists.

    Returns:
        ``True`` when the image is available.
    """
    dockerfile_path = "tdesktop/Telegram/build/docker/centos_env"
    image_name = "tdesktop:centos_env"

    if not os.path.isdir(dockerfile_path):
        logger.error("Dockerfile path non trovato: %s", dockerfile_path)
        return False

    if not force_rebuild and _report_existing_image(image_name):
        return True

    logger.info("Build dell'immagine Docker in corso da %s...", dockerfile_path)
    return _build_image_and_report(image_name, dockerfile_path)


def _resolve_cpus(cpus: str) -> tuple[int, int]:
    """Cap requested CPUs to the number available.

    Args:
        cpus: Requested CPU count, optionally suffixed with ``+``.

    Returns:
        Requested (capped) and available CPU counts.
    """
    available = get_system_cpus()
    return min(int(cpus.rstrip("+")), available), available


def run_build(
    apiid: str,
    apihash: str,
    options: BuildOptions = DEFAULT_OPTIONS,
) -> bool:
    """Run the Telegram Desktop build inside Docker.

    Args:
        apiid: Raw Telegram API ID input.
        apihash: Raw Telegram API hash input.
        options: Container limits and extra CMake flags.

    Returns:
        ``True`` when the build command succeeds.
    """
    credentials = _validated_credentials(apiid, apihash)
    if credentials is None:
        return False
    valid_id, valid_hash = credentials

    cwd = os.getcwd()
    cpus = _resolve_cpus(options.cpus)
    _log_build_config(valid_id, valid_hash, options.memory_limit, cpus)
    try:
        cmake_flags = _cmake_flags(valid_id, valid_hash, cpus[0], options.extra_flags)
        run_command(
            _docker_run_command(cwd, cpus[0], options.memory_limit, cmake_flags)
        )
        logger.info("✓ Build completata con successo")

        verify_build_output(os.path.join(cwd, "tdesktop/out/Release/Telegram"))
        return True
    except CommandError as exc:
        logger.exception("✗ Errore build (exit code %s)", exc.returncode)
        logger.error("Controlla l'output di Docker sopra per dettagli.")
        return False


def handle_source_download() -> None:
    """Download the source or patch its account limit interactively.

    Returns:
        None.

    Raises:
        SystemExit: With code 1 when a required step fails.
    """
    if ask_yes_no(
        "Scaricare Telegram Desktop source? (digitare 'n' se la possedete già) [Y/n]: "
    ):
        if not clone_telegram_source():
            sys.exit(1)
        return

    if ask_yes_no("Sostituire il numero massimo di account? [Y/n]: "):
        voipn = input("Quanti account vuoi avere al massimo?: ")
        if not modify_max_accounts(voipn):
            sys.exit(1)


def _ask_advanced_options(options: BuildOptions) -> BuildOptions:
    """Ask for memory, CPU and extra CMake flags.

    Args:
        options: Current values used as defaults.

    Returns:
        Updated build options.
    """
    if not ask_yes_no("Mostrare opzioni avanzate? [y/N]: ", default=False):
        return options
    return BuildOptions(
        memory_limit=_asked_value(
            f"Memory limit (default {options.memory_limit}): ", options.memory_limit
        ),
        cpus=_asked_value(f"CPU cores (default {options.cpus}): ", options.cpus),
        extra_flags=_asked_value(
            f"CMake flags extra (default {_flag_preview(options.extra_flags)}): ",
            options.extra_flags,
        ),
    )


def handle_docker_build(
    force_rebuild: bool = False,
    options: BuildOptions = DEFAULT_OPTIONS,
) -> None:
    """Build the image and launch the build with interactive credentials.

    Args:
        force_rebuild: Rebuild the image even when present.
        options: Container limits and extra CMake flags.

    Returns:
        None.

    Raises:
        SystemExit: With code 1 when the image or the build fails.
    """
    if not build_docker_image(force_rebuild=force_rebuild):
        sys.exit(1)

    apiid = input("Inserisci il tuo API ID: ")
    apihash = input("Inserisci il tuo API hash: ")
    options = _ask_advanced_options(options)

    if not ask_yes_no("Continuare con la build? [Y/n]: "):
        logger.info("Build annullata.")
        return
    if not run_build(apiid, apihash, options):
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with build and logging options.
    """
    parser = argparse.ArgumentParser(
        description="Build custom Telegram Desktop with multi-account support"
    )
    parser.add_argument(
        "--force-rebuild", action="store_true", help="Force Docker image rebuild"
    )
    parser.add_argument(
        "--memory", default="4g", help="Docker memory limit (default: 4g)"
    )
    parser.add_argument("--cpus", default="2", help="Docker CPU count (default: 2)")
    parser.add_argument("--cmake-flags", default="", help="Extra CMake flags")
    parser.add_argument(
        "--log-dir", default="tdesktop", help="Log directory (default: tdesktop)"
    )
    return parser.parse_args()


def log_banner(log_file: str) -> None:
    """Write the banner with version and system information.

    Args:
        log_file: Path of the active log file.
    """
    logger.info("=" * 80)
    logger.info("Telegram Desktop Multi-Account Builder - v1.3.0")
    logger.info("=" * 80)
    logger.info("Log file: %s", log_file)
    logger.info("Sistema: %s %s", platform.system(), platform.release())
    logger.info("CPU disponibili: %s", get_system_cpus())
    logger.info("")


def main() -> None:
    """Run the interactive builder workflow.

    Returns:
        None.
    """
    args = parse_args()
    log_banner(setup_logging(args.log_dir))

    if ask_yes_no("Installare requisiti Docker? [Y/n]: "):
        install_dependencies()
        logger.info("")

    handle_source_download()
    logger.info("")

    if ask_yes_no("Usare Docker e buildare il source? [Y/n]: "):
        handle_docker_build(
            force_rebuild=args.force_rebuild,
            options=BuildOptions(args.memory, args.cpus, args.cmake_flags),
        )
    else:
        logger.info("Source code non trovato e build saltata.")

    logger.info("=" * 80)
    logger.info("Workflow completato")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
