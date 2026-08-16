import os
import subprocess
import sys


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
    print("Installazione dei prerequisiti in corso...")
    try:
        subprocess.run(
            ["sudo", "apt", "install", "-y", "apt-transport-https", "ca-certificates", "curl", "software-properties-common"],
            check=True
        )
        print("✓ Dipendenze base installate")

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
        print("✓ Chiave GPG di Docker aggiunta")

        subprocess.run(
            ["sudo", "add-apt-repository", "-y", "deb [arch=amd64] https://download.docker.com/linux/ubuntu focal stable"],
            check=True
        )
        print("✓ Repository di Docker aggiunto")

        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "docker-ce"], check=True)
        print("✓ Docker installato")

        subprocess.run(["sudo", "systemctl", "start", "docker"], check=True)
        subprocess.run(["sudo", "systemctl", "status", "docker"], check=True)
        print("✓ Docker avviato con successo")
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore durante l'installazione dei prerequisiti (exit code {e.returncode})")
        sys.exit(1)


def clone_telegram_source():
    """Clone Telegram Desktop source repository."""
    if os.path.isdir("tdesktop"):
        print("⚠ La directory tdesktop esiste già. Saltando il clone...")
        return True

    print("Clonazione del source code di Telegram Desktop in corso (questo può richiedere qualche minuto)...")
    try:
        subprocess.run(
            ["git", "clone", "--recursive", "https://github.com/telegramdesktop/tdesktop.git"],
            check=True
        )
        print("✓ Source code clonato con successo")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore durante il clone (exit code {e.returncode})")
        return False


def modify_max_accounts(voipn):
    """Modify kMaxAccounts constant in main_domain.h."""
    main_domain_path = "tdesktop/Telegram/SourceFiles/main/main_domain.h"

    if not os.path.isfile(main_domain_path):
        print(f"✗ File non trovato: {main_domain_path}")
        return False

    try:
        voipn = validate_voip_count(voipn)
    except ValueError as e:
        print(f"✗ {e}")
        return False

    try:
        with open(main_domain_path, "rt", encoding="utf-8") as fin:
            content = fin.read()

        original_line = "static constexpr auto kMaxAccounts = 3;"
        new_line = f"static constexpr auto kMaxAccounts = {voipn};"

        if original_line not in content:
            print(f"✗ Pattern non trovato in {main_domain_path}")
            return False

        modified_content = content.replace(original_line, new_line)

        with open(main_domain_path, "wt", encoding="utf-8") as fout:
            fout.write(modified_content)

        print(f"✓ kMaxAccounts modificato a {voipn}")
        return True
    except IOError as e:
        print(f"✗ Errore durante la modifica del file: {e}")
        return False


def build_docker_image():
    """Build Docker image for CentOS build environment."""
    dockerfile_path = "tdesktop/Telegram/build/docker/centos_env"

    if not os.path.isdir(dockerfile_path):
        print(f"✗ Dockerfile path non trovato: {dockerfile_path}")
        return False

    print(f"Build dell'immagine Docker in corso da {dockerfile_path}...")
    try:
        subprocess.run(
            ["docker", "build", "-t", "tdesktop:centos_env", dockerfile_path],
            check=True
        )
        print("✓ Immagine Docker creata con successo")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore durante la build dell'immagine Docker (exit code {e.returncode})")
        return False


def run_build(apiid, apihash):
    """Run the Docker build with API credentials."""
    try:
        apiid = validate_api_id(apiid)
        apihash = validate_api_hash(apihash)
    except ValueError as e:
        print(f"✗ {e}")
        return False

    cwd = os.getcwd()
    build_cmd = [
        "docker", "run", "--rm", "-it",
        "-v", f"{cwd}:/usr/src/tdesktop",
        "-e", "DEBUG=1",
        "tdesktop:centos_env",
        "/usr/src/tdesktop/Telegram/build/docker/centos_env/build.sh",
        f"-DTDESKTOP_API_ID={apiid}",
        f"-DTDESKTOP_API_HASH={apihash}",
        "-DDESKTOP_APP_USE_PACKAGED=OFF",
        "-DDESKTOP_APP_DISABLE_CRASH_REPORTS=OFF"
    ]

    print("Avvio della build in Docker...")
    try:
        subprocess.run(build_cmd, check=True)
        print("✓ Build completata con successo")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Errore durante la build (exit code {e.returncode})")
        print("Controlla l'output di Docker sopra per maggiori dettagli.")
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


def handle_docker_build():
    """Handle Docker build process."""
    if not build_docker_image():
        sys.exit(1)

    apiid = input("Inserisci il tuo API ID: ")
    apihash = input("Inserisci il tuo API hash: ")

    if input("Continuare con la build? [Y/n]: ").upper() == "Y":
        if not run_build(apiid, apihash):
            sys.exit(1)
    else:
        print("Build annullata.")


def main():
    """Main workflow."""
    print("=== Telegram Desktop Multi-Account Builder ===\n")

    if input("Installare requisiti Docker? [Y/n]: ").upper() == "Y":
        install_dependencies()
        print()

    handle_source_download()
    print()

    if input("Usare Docker e buildare il source? [Y/n]: ").upper() == "Y":
        handle_docker_build()
    else:
        print("Source code non trovato e build saltata.")


if __name__ == "__main__":
    main()