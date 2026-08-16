import os
import subprocess
import sys
import json
import re
import logging
from datetime import datetime
from pathlib import Path


def setup_logging(log_dir="tdesktop"):
    """Setup logging with file and console output."""
    # Prevent path traversal attacks
    base_dir = Path.cwd()
    log_path = (base_dir / log_dir).resolve()

    # Ensure log_path is within base_dir (no traversal outside)
    try:
        log_path.relative_to(base_dir)
    except ValueError:
        logging.warning(f"Log directory {log_dir} attempts path traversal. Using default 'tdesktop'")
        log_path = base_dir / "tdesktop"

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
    """Check if Docker image already exists."""
    try:
        result = subprocess.run(
            ["docker", "images", "-q", image_name],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        logging.exception("Failed to check Docker images")
        return False


def get_docker_image_info(image_name):
    """Get Docker image metadata."""
    try:
        result = subprocess.run(
            ["docker", "inspect", image_name],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)[0]
    except (subprocess.CalledProcessError, json.JSONDecodeError, IndexError):
        return None


def get_system_cpus():
    """Get number of CPU cores."""
    try:
        return len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else os.cpu_count() or 2
    except (AttributeError, OSError):
        return 2


def validate_voip_count(voipn):
    """Validate that voipn is a positive integer."""
    if not voipn.isdigit():
        raise ValueError("Il numero di account deve essere un numero intero positivo.")
    count = int(voipn)
    if count <= 0:
        raise ValueError("Il numero di account deve essere positivo.")
    return str(count)


def validate_api_id(apiid):
    """Validate API ID format (numeric, non-empty)."""
    apiid = apiid.strip()
    if not apiid:
        raise ValueError("API ID non può essere vuoto.")
    if not apiid.isdigit():
        raise ValueError("API ID deve essere un numero intero.")
    return apiid


def validate_api_hash(apihash):
    """Validate API hash format (non-empty, alphanumeric)."""
    apihash = apihash.strip()
    if not apihash:
        raise ValueError("API hash non può essere vuoto.")
    if not all(c.isalnum() for c in apihash):
        raise ValueError("API hash deve contenere solo caratteri alfanumerici.")
    return apihash


def install_dependencies():
    """Install Docker prerequisites."""
    logging.info("Installazione dei prerequisiti Docker in corso...")
    try:
        logging.info("  • Installazione dipendenze base...")
        subprocess.run(
            ["sudo", "apt", "install", "-y", "apt-transport-https", "ca-certificates", "curl", "software-properties-common"],
            check=True
        )
        logging.info("  ✓ Dipendenze base installate")

        logging.info("  • Aggiunta chiave GPG di Docker...")
        result = subprocess.run(
            ["curl", "-fsSL", "https://download.docker.com/linux/ubuntu/gpg"],
            check=True,
            capture_output=True,
            text=True
        )
        subprocess.run(
            ["sudo", "apt-key", "add", "-"],
            input=result.stdout,
            check=True,
            text=True
        )
        logging.info("  ✓ Chiave GPG aggiunta")

        logging.info("  • Aggiunta repository Docker...")
        subprocess.run(
            ["sudo", "add-apt-repository", "-y", "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"],
            check=True
        )
        logging.info("  ✓ Repository aggiunto")

        logging.info("  • Aggiornamento package manager...")
        subprocess.run(["sudo", "apt", "update"], check=True)

        logging.info("  • Installazione Docker CE...")
        subprocess.run(["sudo", "apt", "install", "-y", "docker-ce"], check=True)
        logging.info("  ✓ Docker installato")

        logging.info("  • Avvio Docker daemon...")
        subprocess.run(["sudo", "systemctl", "start", "docker"], check=True)
        subprocess.run(["sudo", "systemctl", "status", "docker"], check=True)
        logging.info("✓ Docker avviato con successo")
    except subprocess.CalledProcessError as e:
        logging.exception(f"✗ Errore installazione (exit code {e.returncode})")
        sys.exit(1)


def clone_telegram_source():
    """Clone Telegram Desktop source repository."""
    if os.path.isdir("tdesktop"):
        logging.warning("La directory tdesktop esiste già. Saltando il clone...")
        return True

    logging.info("Clonazione source code di Telegram Desktop in corso (può richiedere alcuni minuti)...")
    try:
        subprocess.run(
            ["git", "clone", "--recursive", "https://github.com/telegramdesktop/tdesktop.git"],
            check=True
        )
        logging.info("✓ Source code clonato con successo")
        return True
    except subprocess.CalledProcessError as e:
        logging.exception(f"✗ Errore clone (exit code {e.returncode})")
        return False


def verify_build_output(binary_path):
    """Verify build output and copy to output directory."""
    if os.path.isfile(binary_path):
        file_size = os.path.getsize(binary_path) / (1024**2)  # MB
        mod_time = datetime.fromtimestamp(os.path.getmtime(binary_path))

        logging.info(f"✓ Binary trovato: {binary_path}")
        logging.info(f"  Dimensione: {file_size:.2f} MB")
        logging.info(f"  Modificato: {mod_time}")

        # Copy to output directory
        output_dir = "telegram_output"
        Path(output_dir).mkdir(exist_ok=True)
        output_path = os.path.join(output_dir, "Telegram")

        try:
            import shutil
            shutil.copy2(binary_path, output_path)
            logging.info(f"✓ Binary copiato in: {output_path}")
            return True
        except Exception as e:
            logging.warning(f"Impossibile copiare binary: {e}")
            return True  # Don't fail if copy fails
    else:
        logging.warning(f"Binary non trovato: {binary_path}")
        return False


def modify_max_accounts(voipn):
    """Modify kMaxAccounts constant in main_domain.h with regex support."""
    main_domain_path = "tdesktop/Telegram/SourceFiles/main/main_domain.h"

    if not os.path.isfile(main_domain_path):
        logging.error(f"File non trovato: {main_domain_path}")
        return False

    try:
        voipn = validate_voip_count(voipn)
    except ValueError as e:
        logging.exception(str(e))
        return False

    try:
        with open(main_domain_path, "rt", encoding="utf-8") as fin:
            content = fin.read()

        # Use regex to handle different formatting/whitespace
        pattern = r'static\s+constexpr\s+auto\s+kMaxAccounts\s*=\s*(\d+)\s*;'
        match = re.search(pattern, content)

        if not match:
            logging.error(f"Pattern kMaxAccounts non trovato in {main_domain_path}")
            logging.error("Controlla se il file è della versione corretta di Telegram")
            return False

        old_value = match.group(1)
        modified_content = re.sub(pattern, f'static constexpr auto kMaxAccounts = {voipn};', content)

        with open(main_domain_path, "wt", encoding="utf-8") as fout:
            fout.write(modified_content)

        logging.info(f"✓ kMaxAccounts modificato: {old_value} → {voipn}")
        return True
    except IOError as e:
        logging.exception(f"Errore modifica file: {e}")
        return False


def build_docker_image(force_rebuild=False):
    """Build Docker image for CentOS build environment with caching."""
    dockerfile_path = "tdesktop/Telegram/build/docker/centos_env"
    image_name = "tdesktop:centos_env"

    if not os.path.isdir(dockerfile_path):
        logging.error(f"Dockerfile path non trovato: {dockerfile_path}")
        return False

    # Check if image already exists
    if docker_image_exists(image_name) and not force_rebuild:
        image_info = get_docker_image_info(image_name)
        if image_info:
            created = image_info.get('Created', 'unknown')
            size = image_info.get('Size', 0) / (1024**3)  # Convert to GB
            logging.info(f"✓ Immagine Docker esiste già: {image_name}")
            logging.info(f"  Creata: {created}, Dimensione: {size:.2f}GB")
            return True

    logging.info(f"Build dell'immagine Docker in corso da {dockerfile_path}...")

    try:
        build_cmd = [
            "docker", "build",
            "--progress", "plain",
            "--build-arg", "BUILDKIT_INLINE_CACHE=1",
            "-t", image_name,
            dockerfile_path
        ]

        subprocess.run(build_cmd, check=True)
        logging.info("✓ Immagine Docker creata con successo")

        # Get image info after build
        image_info = get_docker_image_info(image_name)
        if image_info:
            size = image_info.get('Size', 0) / (1024**3)
            logging.info(f"  Dimensione finale: {size:.2f}GB")

        return True
    except subprocess.CalledProcessError as e:
        logging.exception(f"✗ Errore build Docker (exit code {e.returncode})")
        return False


def run_build(apiid, apihash, memory_limit="4g", cpus="2", extra_flags=""):
    """Run the Docker build with API credentials and resource limits."""
    try:
        apiid = validate_api_id(apiid)
        apihash = validate_api_hash(apihash)
    except ValueError as e:
        logging.exception(str(e))
        return False

    cwd = os.getcwd()
    cpus_available = get_system_cpus()
    cpus_requested = min(int(cpus.rstrip('+')), cpus_available)

    logging.info("Configurazione build:")
    logging.info(f"  Memory limit: {memory_limit}")
    logging.info(f"  CPUs: {cpus_requested}/{cpus_available}")
    logging.info(f"  API ID: {apiid[:3]}***")
    logging.info(f"  API Hash: {apihash[:6]}***...")

    # Base CMake flags
    cmake_flags = [
        f"-DTDESKTOP_API_ID={apiid}",
        f"-DTDESKTOP_API_HASH={apihash}",
        "-DDESKTOP_APP_USE_PACKAGED=OFF",
        "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF",
        f"-DCMAKE_BUILD_PARALLEL_LEVEL={cpus_requested}"
    ]

    # Add extra flags if provided
    if extra_flags:
        cmake_flags.extend(extra_flags.split())

    build_cmd = [
        "docker", "run", "--rm", "-it",
        "-m", memory_limit,
        "--cpus", str(cpus_requested),
        "-v", f"{cwd}:/usr/src/tdesktop",
        "-e", "DEBUG=1",
        "-e", f"MAKEFLAGS=-j{cpus_requested}",
        "tdesktop:centos_env",
        "/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh"
    ] + cmake_flags

    logging.info("Avvio della build in Docker...")
    try:
        subprocess.run(build_cmd, check=True)
        logging.info("✓ Build completata con successo")

        # Verify output
        output_binary = os.path.join(cwd, "tdesktop/out/Release/Telegram")
        if verify_build_output(output_binary):
            return True
        else:
            logging.warning("Build completata ma output non verificato")
            return True  # Build succeeded anyway

    except subprocess.CalledProcessError as e:
        logging.exception(f"✗ Errore build (exit code {e.returncode})")
        logging.error("Controlla l'output di Docker sopra per dettagli.")
        return False


def handle_source_download():
    """Handle source code download and modification."""
    if input("Scaricare Telegram Desktop source? (digitare 'n' se la possedete già) [Y/n]: ").upper() == "Y":
        if not clone_telegram_source():
            sys.exit(1)
        return

    if input("Sostituire il numero massimo di account? [Y/n]: ").upper() == "Y":
        voipn = input("Quanti account vuoi avere al massimo?: ")
        if not modify_max_accounts(voipn):
            sys.exit(1)


def handle_docker_build(force_rebuild=False, memory="4g", cpus="2", cmake_flags=""):
    """Handle Docker build process with configuration."""
    if not build_docker_image(force_rebuild=force_rebuild):
        sys.exit(1)

    apiid = input("Inserisci il tuo API ID: ")
    apihash = input("Inserisci il tuo API hash: ")

    # Show advanced options
    show_advanced = input("Mostrare opzioni avanzate? [y/N]: ").upper() == "Y"
    if show_advanced:
        memory = input(f"Memory limit (default {memory}): ") or memory
        cpus = input(f"CPU cores (default {cpus}): ") or cpus
        cmake_flags = input("CMake flags extra (default vuoto): ") or ""

    if input("Continuare con la build? [Y/n]: ").upper() == "Y":
        if not run_build(apiid, apihash, memory_limit=memory, cpus=cpus, extra_flags=cmake_flags):
            sys.exit(1)
    else:
        logging.info("Build annullata.")


def main():
    """Main workflow with logging and advanced options."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build custom Telegram Desktop with multi-account support"
    )
    parser.add_argument("--force-rebuild", action="store_true", help="Force Docker image rebuild")
    parser.add_argument("--memory", default="4g", help="Docker memory limit (default: 4g)")
    parser.add_argument("--cpus", default="2", help="Docker CPU count (default: 2)")
    parser.add_argument("--cmake-flags", default="", help="Extra CMake flags")
    parser.add_argument("--log-dir", default="tdesktop", help="Log directory (default: tdesktop)")
    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(args.log_dir)
    logging.info("=" * 80)
    logging.info("Telegram Desktop Multi-Account Builder - v1.3.0")
    logging.info("=" * 80)
    logging.info(f"Log file: {log_file}")
    logging.info(f"Sistema: {os.uname().sysname} {os.uname().release}")
    logging.info(f"CPU disponibili: {get_system_cpus()}")
    logging.info("")

    if input("Installare requisiti Docker? [Y/n]: ").upper() == "Y":
        install_dependencies()
        logging.info("")

    handle_source_download()
    logging.info("")

    if input("Usare Docker e buildare il source? [Y/n]: ").upper() == "Y":
        handle_docker_build(
            force_rebuild=args.force_rebuild,
            memory=args.memory,
            cpus=args.cpus,
            cmake_flags=args.cmake_flags
        )
    else:
        logging.info("Source code non trovato e build saltata.")

    logging.info("=" * 80)
    logging.info("Workflow completato")
    logging.info("=" * 80)


if __name__ == "__main__":
    main()