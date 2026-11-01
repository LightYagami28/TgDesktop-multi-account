"""Costruisce Telegram Desktop con il limite di account personalizzato, dentro Docker."""
import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from source_patch import modify_max_accounts
from validation import ask_yes_no, validate_api_hash, validate_api_id


def run_command(cmd, **kwargs):
    """Esegue un comando con il percorso completo dell'eseguibile (nessuna shell)."""
    executable = shutil.which(cmd[0])
    if executable is None:
        raise FileNotFoundError(f"Comando non trovato: {cmd[0]}")
    return subprocess.run([executable, *cmd[1:]], check=True, **kwargs)


def _confined_log_path(log_dir):
    """Percorso del log, confinato nella cartella corrente."""
    base_dir = Path.cwd()
    log_path = (base_dir / log_dir).resolve()
    try:
        log_path.relative_to(base_dir)
    except ValueError:
        logging.warning(
            "Log directory %s attempts path traversal. Using default 'tdesktop'", log_dir
        )
        return base_dir / "tdesktop"
    return log_path


def setup_logging(log_dir="tdesktop"):
    """Configura il logging su file e console; restituisce il percorso del log."""
    log_path = _confined_log_path(log_dir)
    log_path.mkdir(exist_ok=True, parents=True)
    log_file = str(log_path / f"telegram_build_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

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
        result = run_command(["docker", "images", "-q", image_name], capture_output=True, text=True)
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logging.exception("Failed to check Docker images")
        return False


def get_docker_image_info(image_name):
    """Restituisce i metadati dell'immagine Docker o None."""
    try:
        result = run_command(["docker", "inspect", image_name], capture_output=True, text=True)
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


APT_PREREQUISITES = ["ca-certificates", "curl"]
DOCKER_KEYRING = "/etc/apt/keyrings/docker.asc"
DOCKER_SOURCE_FILE = "/etc/apt/sources.list.d/docker.list"


def docker_apt_source(codename, arch):
    """Riga del repository Docker, firmata dal keyring dedicato."""
    return (
        f"deb [arch={arch} signed-by={DOCKER_KEYRING}] "
        f"https://download.docker.com/linux/ubuntu {codename} stable\n"
    )


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
    run_command(["sudo", "tee", DOCKER_SOURCE_FILE], input=docker_apt_source(codename, arch),
                text=True, stdout=subprocess.DEVNULL)


def _install_docker_ce():
    """Installa Docker CE dal repository aggiunto e avvia il daemon."""
    logging.info("  • Installazione di Docker CE e avvio del daemon...")
    run_command(["sudo", "apt", "update"])
    run_command(["sudo", "apt", "install", "-y", "docker-ce"])
    run_command(["sudo", "systemctl", "start", "docker"])
    run_command(["sudo", "systemctl", "status", "docker"])


def install_dependencies():
    """Installa Docker CE su Ubuntu/Debian."""
    logging.info("Installazione dei prerequisiti Docker in corso...")
    try:
        logging.info("  • Installazione dipendenze base...")
        run_command(["sudo", "apt", "install", "-y", *APT_PREREQUISITES])
        logging.info("  ✓ Dipendenze base installate")

        logging.info("  • Aggiunta chiave GPG e repository di Docker...")
        _add_docker_key()
        _add_docker_repo()
        logging.info("  ✓ Chiave e repository aggiunti")

        _install_docker_ce()
        logging.info("✓ Docker installato e avviato")
    except subprocess.CalledProcessError as exc:
        logging.exception("✗ Errore installazione (exit code %s)", exc.returncode)
        sys.exit(1)


TDESKTOP_REPO = "https://github.com/telegramdesktop/tdesktop.git"


def clone_telegram_source():
    """Clona il sorgente di Telegram Desktop se manca."""
    if os.path.isdir("tdesktop"):
        logging.warning("La directory tdesktop esiste già. Saltando il clone...")
        return True

    logging.info("Clonazione source code di Telegram Desktop in corso (alcuni minuti)...")
    try:
        run_command(["git", "clone", "--recursive", TDESKTOP_REPO])
        logging.info("✓ Source code clonato con successo")
        return True
    except subprocess.CalledProcessError as exc:
        logging.exception("✗ Errore clone (exit code %s)", exc.returncode)
        return False


def verify_build_output(binary_path):
    """Controlla il binario compilato e ne copia una versione in telegram_output."""
    if not os.path.isfile(binary_path):
        logging.warning("Binary non trovato: %s", binary_path)
        return False

    file_size = os.path.getsize(binary_path) / (1024**2)  # MB
    mod_time = datetime.fromtimestamp(os.path.getmtime(binary_path))

    logging.info("✓ Binary trovato: %s", binary_path)
    logging.info("  Dimensione: %.2f MB", file_size)
    logging.info("  Modificato: %s", mod_time)

    output_dir = "telegram_output"
    Path(output_dir).mkdir(exist_ok=True)
    output_path = os.path.join(output_dir, "Telegram")

    try:
        shutil.copy2(binary_path, output_path)
        logging.info("✓ Binary copiato in: %s", output_path)
    except OSError as exc:
        logging.warning("Impossibile copiare binary: %s", exc)
    return True  # la copia è facoltativa


def _log_image_size(image_info, label):
    size = image_info.get('Size', 0) / (1024**3)  # GB
    logging.info("  %s: %.2fGB", label, size)


def _report_existing_image(image_name):
    """Logga l'immagine già presente; False se manca o non è leggibile."""
    if not docker_image_exists(image_name):
        return False
    image_info = get_docker_image_info(image_name)
    if not image_info:
        return False
    logging.info("✓ Immagine Docker esiste già: %s", image_name)
    logging.info("  Creata: %s", image_info.get('Created', 'unknown'))
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


def build_docker_image(force_rebuild=False):
    """Costruisce l'immagine Docker di build, se manca o se richiesto."""
    dockerfile_path = "tdesktop/Telegram/build/docker/centos_env"
    image_name = "tdesktop:centos_env"

    if not os.path.isdir(dockerfile_path):
        logging.error("Dockerfile path non trovato: %s", dockerfile_path)
        return False

    if not force_rebuild and _report_existing_image(image_name):
        return True

    logging.info("Build dell'immagine Docker in corso da %s...", dockerfile_path)

    try:
        _docker_build(image_name, dockerfile_path)
        logging.info("✓ Immagine Docker creata con successo")

        image_info = get_docker_image_info(image_name)
        if image_info:
            _log_image_size(image_info, "Dimensione finale")

        return True
    except subprocess.CalledProcessError as exc:
        logging.exception("✗ Errore build Docker (exit code %s)", exc.returncode)
        return False


def _docker_run_command(cwd, cpus, memory_limit, cmake_flags):
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


def _cmake_flags(apiid, apihash, cpus, extra_flags):
    return [
        f"-DTDESKTOP_API_ID={apiid}",
        f"-DTDESKTOP_API_HASH={apihash}",
        "-DDESKTOP_APP_USE_PACKAGED=OFF",
        "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF",
        f"-DCMAKE_BUILD_PARALLEL_LEVEL={cpus}",
        *extra_flags.split(),
    ]


def _log_build_config(apiid, apihash, memory_limit, cpus_requested, cpus_available):
    """Logga la configurazione, con le credenziali mascherate."""
    logging.info("Configurazione build:")
    logging.info("  Memory limit: %s, CPUs: %s/%s", memory_limit, cpus_requested, cpus_available)
    logging.info("  API ID: %s***, API Hash: %s***...", apiid[:3], apihash[:6])
    logging.info("Avvio della build in Docker...")


def _resolve_cpus(cpus):
    """CPU richieste (limitate a quelle disponibili) e CPU disponibili."""
    available = get_system_cpus()
    return min(int(cpus.rstrip('+')), available), available


def run_build(apiid, apihash, memory_limit="4g", cpus="2", extra_flags=""):
    """Avvia la build di Telegram Desktop nel container."""
    try:
        apiid = validate_api_id(apiid)
        apihash = validate_api_hash(apihash)
    except ValueError as exc:
        logging.exception(str(exc))
        return False

    cwd = os.getcwd()
    cpus_requested, cpus_available = _resolve_cpus(cpus)
    _log_build_config(apiid, apihash, memory_limit, cpus_requested, cpus_available)
    try:
        cmake_flags = _cmake_flags(apiid, apihash, cpus_requested, extra_flags)
        run_command(_docker_run_command(cwd, cpus_requested, memory_limit, cmake_flags))
        logging.info("✓ Build completata con successo")

        verify_build_output(os.path.join(cwd, "tdesktop/out/Release/Telegram"))
        return True  # la build è riuscita anche se l'output non è verificabile

    except subprocess.CalledProcessError as exc:
        logging.exception("✗ Errore build (exit code %s)", exc.returncode)
        logging.error("Controlla l'output di Docker sopra per dettagli.")
        return False


def handle_source_download():
    """Scarica il sorgente o ne modifica il limite di account."""
    if ask_yes_no("Scaricare Telegram Desktop source? (digitare 'n' se la possedete già) [Y/n]: "):
        if not clone_telegram_source():
            sys.exit(1)
        return

    if ask_yes_no("Sostituire il numero massimo di account? [Y/n]: "):
        voipn = input("Quanti account vuoi avere al massimo?: ")
        if not modify_max_accounts(voipn):
            sys.exit(1)


def handle_docker_build(force_rebuild=False, memory="4g", cpus="2", cmake_flags=""):
    """Costruisce l'immagine e lancia la build chiedendo i dati all'utente."""
    if not build_docker_image(force_rebuild=force_rebuild):
        sys.exit(1)

    apiid = input("Inserisci il tuo API ID: ")
    apihash = input("Inserisci il tuo API hash: ")

    if ask_yes_no("Mostrare opzioni avanzate? [y/N]: ", default=False):
        memory = input(f"Memory limit (default {memory}): ") or memory
        cpus = input(f"CPU cores (default {cpus}): ") or cpus
        cmake_flags = input("CMake flags extra (default vuoto): ") or ""

    if ask_yes_no("Continuare con la build? [Y/n]: "):
        if not run_build(apiid, apihash, memory_limit=memory, cpus=cpus, extra_flags=cmake_flags):
            sys.exit(1)
    else:
        logging.info("Build annullata.")


def parse_args():
    """Legge gli argomenti da riga di comando."""
    parser = argparse.ArgumentParser(
        description="Build custom Telegram Desktop with multi-account support"
    )
    parser.add_argument("--force-rebuild", action="store_true", help="Force Docker image rebuild")
    parser.add_argument("--memory", default="4g", help="Docker memory limit (default: 4g)")
    parser.add_argument("--cpus", default="2", help="Docker CPU count (default: 2)")
    parser.add_argument("--cmake-flags", default="", help="Extra CMake flags")
    parser.add_argument("--log-dir", default="tdesktop", help="Log directory (default: tdesktop)")
    return parser.parse_args()


def log_banner(log_file):
    """Scrive l'intestazione con versione e informazioni di sistema."""
    logging.info("=" * 80)
    logging.info("Telegram Desktop Multi-Account Builder - v1.3.0")
    logging.info("=" * 80)
    logging.info("Log file: %s", log_file)
    logging.info("Sistema: %s %s", platform.system(), platform.release())
    logging.info("CPU disponibili: %s", get_system_cpus())
    logging.info("")


def main():
    """Punto di ingresso del builder."""
    args = parse_args()
    log_banner(setup_logging(args.log_dir))

    if ask_yes_no("Installare requisiti Docker? [Y/n]: "):
        install_dependencies()
        logging.info("")

    handle_source_download()
    logging.info("")

    if ask_yes_no("Usare Docker e buildare il source? [Y/n]: "):
        handle_docker_build(
            force_rebuild=args.force_rebuild,
            memory=args.memory,
            cpus=args.cpus,
            cmake_flags=args.cmake_flags,
        )
    else:
        logging.info("Source code non trovato e build saltata.")

    logging.info("=" * 80)
    logging.info("Workflow completato")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()
