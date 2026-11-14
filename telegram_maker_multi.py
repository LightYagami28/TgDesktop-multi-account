"""Costruisce Telegram Desktop con limite di account personalizzato, dentro Docker."""
import argparse
import json
import logging
import os
import platform
import shutil

# Il builder deve lanciare docker, git e apt: subprocess è usato solo tramite
# run_command, senza shell e con l'eseguibile risolto a percorso completo.
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path

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
from source_patch import modify_max_accounts
from validation import ask_yes_no

logger = logging.getLogger(__name__)


def run_command(cmd, **kwargs):
    """Esegue un comando con il percorso completo dell'eseguibile (nessuna shell)."""
    executable = shutil.which(cmd[0])
    if executable is None:
        raise FileNotFoundError(f"Comando non trovato: {cmd[0]}")
    # Lista di argomenti, mai shell=True: gli input dell'utente (API ID, hash,
    # numero di account) sono validati prima e restano argomenti separati.
    argv = [executable, *cmd[1:]]
    return subprocess.run(*argv, check=True, **kwargs)  # nosec B603  # nosemgrep


def setup_logging(log_dir="tdesktop"):
    """Configura il logging su file e console; restituisce il percorso del log."""
    log_path = _confined_log_path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    log_file = str(log_path / f"telegram_build_{datetime.now():%Y%m%d_%H%M%S}.log")

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return log_file


def docker_image_exists(image_name):
    """Dice se l'immagine Docker esiste in locale."""
    try:
        result = run_command(
            ["docker", "images", "-q", image_name], capture_output=True, text=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logger.exception("Failed to check Docker images")
        return False


def get_docker_image_info(image_name):
    """Restituisce i metadati dell'immagine Docker o None."""
    try:
        result = run_command(
            ["docker", "inspect", image_name], capture_output=True, text=True
        )
        return json.loads(result.stdout)[0]
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
        return None


def get_system_cpus():
    """Numero di CPU utilizzabili (2 se non rilevabile)."""
    try:
        if hasattr(os, 'sched_getaffinity'):
            return len(os.sched_getaffinity(0))
        return os.cpu_count() or 2
    except (AttributeError, OSError):
        return 2


def _add_docker_key():
    """Scarica la chiave GPG di Docker nel keyring dedicato."""
    key = run_command(
        ["curl", "-fsSL", "https://download.docker.com/linux/ubuntu/gpg"],
        capture_output=True, text=True,
    )
    run_command(["sudo", "install", "-d", "-m", "0755", "/etc/apt/keyrings"])
    run_command(["sudo", "tee", DOCKER_KEYRING], input=key.stdout, text=True,
                stdout=subprocess.DEVNULL)
    run_command(["sudo", "chmod", "a+r", DOCKER_KEYRING])


def _add_docker_repo():
    """Scrive il repository Docker per il rilascio e l'architettura correnti."""
    codename = platform.freedesktop_os_release().get("VERSION_CODENAME", "focal")
    arch = run_command(["dpkg", "--print-architecture"],
                       capture_output=True, text=True).stdout.strip()
    run_command(
        ["sudo", "tee", DOCKER_SOURCE_FILE],
        input=docker_apt_source(codename, arch),
        text=True,
        stdout=subprocess.DEVNULL,
    )


def _install_docker_ce():
    """Installa Docker CE dal repository aggiunto e avvia il daemon."""
    logger.info("  • Installazione di Docker CE e avvio del daemon...")
    run_command(["sudo", "apt", "update"])
    run_command(["sudo", "apt", "install", "-y", "docker-ce"])
    run_command(["sudo", "systemctl", "start", "docker"])
    run_command(["sudo", "systemctl", "status", "docker"])


def install_dependencies():
    """Installa Docker CE su Ubuntu/Debian."""
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
    except subprocess.CalledProcessError as exc:
        logger.exception("✗ Errore installazione (exit code %s)", exc.returncode)
        sys.exit(1)


def clone_telegram_source():
    """Clona il sorgente di Telegram Desktop se manca."""
    if os.path.isdir("tdesktop"):
        logger.warning("La directory tdesktop esiste già. Saltando il clone...")
        return True

    logger.info(
        "Clonazione source code di Telegram Desktop in corso (alcuni minuti)..."
    )
    try:
        run_command(["git", "clone", "--recursive", TDESKTOP_REPO])
        logger.info("✓ Source code clonato con successo")
        return True
    except subprocess.CalledProcessError as exc:
        logger.exception("✗ Errore clone (exit code %s)", exc.returncode)
        return False


def verify_build_output(binary_path):
    """Controlla il binario compilato e ne copia una versione in telegram_output."""
    if not os.path.isfile(binary_path):
        logger.warning("Binary non trovato: %s", binary_path)
        return False

    file_size = os.path.getsize(binary_path) / (1024**2)  # MB
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
    return True  # la copia è facoltativa


def _log_image_size(image_info, label):
    size = image_info.get('Size', 0) / (1024**3)  # GB
    logger.info("  %s: %.2fGB", label, size)


def _report_existing_image(image_name):
    """Logga l'immagine già presente; False se manca o non è leggibile."""
    if not docker_image_exists(image_name):
        return False
    image_info = get_docker_image_info(image_name)
    if not image_info:
        return False
    logger.info("✓ Immagine Docker esiste già: %s", image_name)
    logger.info("  Creata: %s", image_info.get('Created', 'unknown'))
    _log_image_size(image_info, "Dimensione")
    return True


def _docker_build(image_name, dockerfile_path):
    run_command([
        "docker", "build",
        "--progress", "plain",
        "--build-arg", "BUILDKIT_INLINE_CACHE=1",
        "-t", image_name,
        dockerfile_path,
    ])


def _build_image_and_report(image_name, dockerfile_path):
    """Costruisce l'immagine e ne logga la dimensione; False se la build fallisce."""
    try:
        _docker_build(image_name, dockerfile_path)
    except subprocess.CalledProcessError as exc:
        logger.exception("✗ Errore build Docker (exit code %s)", exc.returncode)
        return False
    logger.info("✓ Immagine Docker creata con successo")

    image_info = get_docker_image_info(image_name)
    if image_info:
        _log_image_size(image_info, "Dimensione finale")
    return True


def build_docker_image(force_rebuild=False):
    """Costruisce l'immagine Docker di build, se manca o se richiesto."""
    dockerfile_path = "tdesktop/Telegram/build/docker/centos_env"
    image_name = "tdesktop:centos_env"

    if not os.path.isdir(dockerfile_path):
        logger.error("Dockerfile path non trovato: %s", dockerfile_path)
        return False

    if not force_rebuild and _report_existing_image(image_name):
        return True

    logger.info("Build dell'immagine Docker in corso da %s...", dockerfile_path)
    return _build_image_and_report(image_name, dockerfile_path)


def _resolve_cpus(cpus):
    """CPU richieste (limitate a quelle disponibili) e CPU disponibili."""
    available = get_system_cpus()
    return min(int(cpus.rstrip('+')), available), available


def run_build(apiid, apihash, options=DEFAULT_OPTIONS):
    """Avvia la build di Telegram Desktop nel container."""
    credentials = _validated_credentials(apiid, apihash)
    if credentials is None:
        return False
    apiid, apihash = credentials

    cwd = os.getcwd()
    cpus = _resolve_cpus(options.cpus)
    _log_build_config(apiid, apihash, options.memory_limit, cpus)
    try:
        cmake_flags = _cmake_flags(apiid, apihash, cpus[0], options.extra_flags)
        run_command(
            _docker_run_command(cwd, cpus[0], options.memory_limit, cmake_flags)
        )
        logger.info("✓ Build completata con successo")

        verify_build_output(os.path.join(cwd, "tdesktop/out/Release/Telegram"))
        return True  # la build è riuscita anche se l'output non è verificabile

    except subprocess.CalledProcessError as exc:
        logger.exception("✗ Errore build (exit code %s)", exc.returncode)
        logger.error("Controlla l'output di Docker sopra per dettagli.")
        return False


def handle_source_download():
    """Scarica il sorgente o ne modifica il limite di account."""
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


def _ask_advanced_options(options):
    """Chiede memoria, CPU e flag CMake; Invio conserva il valore proposto."""
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


def handle_docker_build(force_rebuild=False, options=DEFAULT_OPTIONS):
    """Costruisce l'immagine e lancia la build chiedendo i dati all'utente."""
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


def parse_args():
    """Legge gli argomenti da riga di comando."""
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


def log_banner(log_file):
    """Scrive l'intestazione con versione e informazioni di sistema."""
    logger.info("=" * 80)
    logger.info("Telegram Desktop Multi-Account Builder - v1.3.0")
    logger.info("=" * 80)
    logger.info("Log file: %s", log_file)
    logger.info("Sistema: %s %s", platform.system(), platform.release())
    logger.info("CPU disponibili: %s", get_system_cpus())
    logger.info("")


def main():
    """Punto di ingresso del builder."""
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
