"""Test di telegram_maker_multi."""
import json
import os

# subprocess fornisce solo eccezioni e risultati finti: nessun comando viene eseguito.
import subprocess  # nosec B404
import tempfile
import unittest
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
from unittest.mock import mock_open, patch

import telegram_maker_multi as tm
from source_patch import modify_max_accounts
from telegram_maker_multi import docker_apt_source, install_dependencies, run_command
from validation import (
    ask_yes_no,
    validate_api_hash,
    validate_api_id,
    validate_voip_count,
)

FAILED = subprocess.CalledProcessError(1, ["docker"])


@contextmanager
def in_temp_dir():
    """Esegue il blocco dentro una cartella temporanea, poi torna alla precedente."""
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        os.chdir(tmp)
        try:
            yield Path(tmp)
        finally:
            os.chdir(previous)


@dataclass
class FakeResult:
    """Risultato finto di run_command."""

    stdout: str = ""
    returncode: int = 0


def completed(stdout=""):
    """Risultato finto di run_command."""
    return FakeResult(stdout)


class TestValidateVoipCount(unittest.TestCase):
    """Test voip count validation."""

    def test_valid_positive_integer(self):
        """Valid positive integer should pass."""
        self.assertEqual(validate_voip_count("5"), "5")
        self.assertEqual(validate_voip_count("1"), "1")
        self.assertEqual(validate_voip_count("999"), "999")

    def test_zero_rejected(self):
        """Zero should be rejected."""
        with self.assertRaises(ValueError):
            validate_voip_count("0")

    def test_negative_rejected(self):
        """Negative numbers should be rejected."""
        with self.assertRaises(ValueError):
            validate_voip_count("-5")

    def test_non_numeric_rejected(self):
        """Non-numeric input should be rejected."""
        with self.assertRaises(ValueError):
            validate_voip_count("abc")
        with self.assertRaises(ValueError):
            validate_voip_count("5.5")
        with self.assertRaises(ValueError):
            validate_voip_count("")

    def test_special_chars_rejected(self):
        """Input with special characters should be rejected."""
        with self.assertRaises(ValueError):
            validate_voip_count("5; rm -rf /")


class TestValidateApiId(unittest.TestCase):
    """Test API ID validation."""

    def test_valid_numeric_id(self):
        """Valid numeric API ID should pass."""
        self.assertEqual(validate_api_id("123456"), "123456")
        self.assertEqual(validate_api_id("9999999"), "9999999")

    def test_non_numeric_rejected(self):
        """Non-numeric API ID should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_id("abc123")
        with self.assertRaises(ValueError):
            validate_api_id("12.34")

    def test_empty_rejected(self):
        """Empty API ID should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_id("")
        with self.assertRaises(ValueError):
            validate_api_id("   ")

    def test_special_chars_rejected(self):
        """API ID with special characters should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_id("123; DROP TABLE")

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        self.assertEqual(validate_api_id("  123456  "), "123456")


class TestValidateApiHash(unittest.TestCase):
    """Test API hash validation."""

    def test_valid_hash(self):
        """Valid alphanumeric hash should pass."""
        self.assertEqual(validate_api_hash("abcdef123456"), "abcdef123456")
        self.assertEqual(validate_api_hash("ABCDEF"), "ABCDEF")
        self.assertEqual(validate_api_hash("abc123"), "abc123")

    def test_empty_rejected(self):
        """Empty API hash should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_hash("")
        with self.assertRaises(ValueError):
            validate_api_hash("   ")

    def test_special_chars_rejected(self):
        """API hash with special characters should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_hash("abc-def")
        with self.assertRaises(ValueError):
            validate_api_hash("abc_def")
        with self.assertRaises(ValueError):
            validate_api_hash("abc@def")

    def test_whitespace_trimmed(self):
        """Leading/trailing whitespace should be trimmed."""
        self.assertEqual(validate_api_hash("  abcdef123456  "), "abcdef123456")

    def test_spaces_rejected(self):
        """Spaces in the middle should be rejected."""
        with self.assertRaises(ValueError):
            validate_api_hash("abc def")


class TestInputSanitization(unittest.TestCase):
    """Test that all validations prevent injection attacks."""

    def test_voip_injection(self):
        """Voip count should reject injection attempts."""
        malicious_inputs = [
            "3; rm -rf /",
            "3 && dangerous_command",
            "3 | cat /etc/passwd",
            "3 `whoami`",
            "3 $(whoami)",
            "3\\nrm -rf /",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(ValueError):
                validate_voip_count(malicious)

    def test_api_id_injection(self):
        """API ID should reject injection attempts."""
        malicious_inputs = [
            "123; DROP TABLE users",
            "123 OR 1=1",
            "123'; --",
            "123\\nmalicious",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(ValueError):
                validate_api_id(malicious)

    def test_api_hash_injection(self):
        """API hash should reject injection attempts."""
        malicious_inputs = [
            "abc; system('evil')",
            "abc$(whoami)",
            "abc`id`",
            "abc|cat",
            "abc&&rm",
        ]
        for malicious in malicious_inputs:
            with self.assertRaises(ValueError):
                validate_api_hash(malicious)


class TestFileOperations(unittest.TestCase):
    """Test file handling edge cases."""

    def test_missing_file(self):
        """Should handle missing file gracefully."""
        with patch("os.path.isfile", return_value=False):
            result = modify_max_accounts("5")
            self.assertFalse(result)

    def test_missing_pattern(self):
        """Should handle missing pattern in file."""
        test_content = "// No kMaxAccounts pattern here\nint some_other_value = 5;\n"

        with patch("os.path.isfile", return_value=True), patch(
            "builtins.open", mock_open(read_data=test_content)
        ):
            result = modify_max_accounts("10")
            self.assertFalse(result)


class TestAskYesNo(unittest.TestCase):
    """Test della conferma [Y/n] / [y/N]."""

    def ask(self, answers, default=True):
        """Esegue ask_yes_no con risposte simulate."""
        feed = iter(answers)
        prompts = []

        def fake_input(prompt):
            prompts.append(prompt)
            try:
                return next(feed)
            except StopIteration as exc:
                raise EOFError from exc

        return ask_yes_no("Domanda? ", default=default, input_func=fake_input), prompts

    def test_enter_uses_default_yes(self):
        """Enter uses default yes."""
        self.assertTrue(self.ask([""])[0])
        self.assertTrue(self.ask(["   "])[0])

    def test_enter_uses_default_no(self):
        """Enter uses default no."""
        self.assertFalse(self.ask([""], default=False)[0])

    def test_yes_answers(self):
        """Yes answers."""
        for answer in ("y", "Y", "yes", "s", "si", "SI", "sì"):
            self.assertTrue(self.ask([answer], default=False)[0], answer)

    def test_no_answers(self):
        """No answers."""
        for answer in ("n", "N", "no", "NO"):
            self.assertFalse(self.ask([answer])[0], answer)

    def test_invalid_answer_asks_again(self):
        """Invalid answer asks again."""
        with self.assertLogs(level="WARNING"):
            result, prompts = self.ask(["forse", "n"])
        self.assertFalse(result)
        self.assertEqual(len(prompts), 2)

    def test_eof_does_not_confirm(self):
        """Eof does not confirm."""
        self.assertFalse(self.ask([])[0])


class TestRunCommand(unittest.TestCase):
    """Test dell'esecuzione dei comandi."""

    def test_missing_executable_raises(self):
        """Un eseguibile assente non viene lanciato."""
        with patch("shutil.which", return_value=None), self.assertRaises(
            FileNotFoundError
        ):
            run_command(["comando-inesistente"])


class TestDockerInstall(unittest.TestCase):
    """Test dell'installazione di Docker."""

    def test_source_signed(self):
        """La riga del repository usa il keyring dedicato."""
        line = docker_apt_source("noble", "amd64")
        self.assertIn("signed-by=/etc/apt/keyrings/docker.asc", line)
        self.assertIn("ubuntu noble stable", line)

    def test_install_no_apt_key(self):
        """Nessun comando usa apt-key."""
        calls = []

        def fake(cmd, **_kwargs):
            calls.append(cmd)
            return type("R", (), {"stdout": "amd64\n"})()

        with patch("telegram_maker_multi.run_command", side_effect=fake), patch(
            "platform.freedesktop_os_release", return_value={"VERSION_CODENAME": "noble"}
        ):
            install_dependencies()
        self.assertFalse(any("apt-key" in c for c in calls))
        self.assertIn(["sudo", "chmod", "a+r", "/etc/apt/keyrings/docker.asc"], calls)



class TestPatchSource(unittest.TestCase):
    """Test della modifica di kMaxAccounts su un file vero."""

    HEADER = "tdesktop/Telegram/SourceFiles/main/main_domain.h"

    def write_header(self, root, content):
        """Crea il file sorgente finto e ne restituisce il percorso."""
        path = root / self.HEADER
        path.parent.mkdir(parents=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_value_replaced(self):
        """Il valore viene sostituito e il resto del file resta uguale."""
        with in_temp_dir() as root:
            path = self.write_header(root, "a;\nstatic constexpr auto kMaxAccounts = 3;\nb;\n")
            with self.assertLogs(level="INFO"):
                self.assertTrue(modify_max_accounts("12"))
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "a;\nstatic constexpr auto kMaxAccounts = 12;\nb;\n",
            )

    def test_invalid_count(self):
        """Un numero non valido non tocca il file."""
        with in_temp_dir() as root:
            path = self.write_header(root, "static constexpr auto kMaxAccounts = 3;\n")
            with self.assertLogs(level="ERROR"):
                self.assertFalse(modify_max_accounts("0"))
            self.assertIn("= 3;", path.read_text(encoding="utf-8"))

    def test_read_error(self):
        """Un errore di lettura viene loggato e restituisce False."""
        with patch("os.path.isfile", return_value=True), patch(
            "builtins.open", side_effect=OSError("negato")
        ), self.assertLogs(level="ERROR"):
            self.assertFalse(modify_max_accounts("5"))


class TestLogging(unittest.TestCase):
    """Test del percorso e della configurazione dei log."""

    def test_path_inside_cwd(self):
        """Una cartella interna viene accettata."""
        with in_temp_dir() as root, patch("logging.FileHandler"), patch(
            "logging.basicConfig"
        ):
            log_file = Path(tm.setup_logging("logs"))
            self.assertEqual(log_file.parent, (root / "logs").resolve())

    def test_path_traversal_blocked(self):
        """Una cartella esterna viene sostituita da tdesktop."""
        with in_temp_dir(), patch("logging.FileHandler"), patch(
            "logging.basicConfig"
        ), self.assertLogs(level="WARNING"):
            log_file = Path(tm.setup_logging("../fuori"))
            self.assertEqual(log_file.parent, Path.cwd() / "tdesktop")

    def test_setup_logging(self):
        """Il file di log sta nella cartella richiesta e ha il timestamp nel nome."""
        with in_temp_dir() as root, patch("logging.basicConfig") as config:
            with patch("logging.FileHandler"):
                log_file = Path(tm.setup_logging("logs"))
            self.assertEqual(log_file.parent, (root / "logs").resolve())
            self.assertRegex(log_file.name, r"^telegram_build_\d{8}_\d{6}\.log$")
            config.assert_called_once()

    def test_banner(self):
        """L'intestazione riporta il file di log."""
        with self.assertLogs(level="INFO") as logs:
            tm.log_banner("build.log")
        self.assertIn("Log file: build.log", "\n".join(logs.output))


class TestRunCommandExec(unittest.TestCase):
    """Test di run_command quando l'eseguibile esiste."""

    def test_full_path_no_shell(self):
        """Il comando parte con il percorso completo, check=True e senza shell."""
        with patch("shutil.which", return_value="/usr/bin/docker"), patch(
            "subprocess.run", return_value=completed()
        ) as run:
            run_command(["docker", "ps"], text=True)
        run.assert_called_once_with("/usr/bin/docker", "ps", check=True, text=True)


class TestDockerQueries(unittest.TestCase):
    """Test delle interrogazioni a Docker."""

    def test_image_exists(self):
        """Un id in output significa immagine presente."""
        with patch.object(tm, "run_command", return_value=completed("abc123\n")):
            self.assertTrue(tm.docker_image_exists("img"))

    def test_image_missing(self):
        """Output vuoto significa immagine assente."""
        with patch.object(tm, "run_command", return_value=completed("\n")):
            self.assertFalse(tm.docker_image_exists("img"))

    def test_image_check_fails(self):
        """Un errore di Docker viene loggato e vale come assente."""
        with patch.object(tm, "run_command", side_effect=FAILED), self.assertLogs(level="ERROR"):
            self.assertFalse(tm.docker_image_exists("img"))

    def test_image_info(self):
        """I metadati sono il primo elemento del JSON di docker inspect."""
        payload = json.dumps([{"Size": 1024**3, "Created": "oggi"}])
        with patch.object(tm, "run_command", return_value=completed(payload)):
            info = tm.get_docker_image_info("img")
        if info is None:
            self.fail("Metadati immagine assenti")
        self.assertEqual(info["Created"], "oggi")

    def test_image_info_unreadable(self):
        """JSON non valido, lista vuota o errore restituiscono None."""
        for result in (completed("non json"), completed("[]")):
            with patch.object(tm, "run_command", return_value=result):
                self.assertIsNone(tm.get_docker_image_info("img"))
        with patch.object(tm, "run_command", side_effect=FAILED):
            self.assertIsNone(tm.get_docker_image_info("img"))


class TestCpus(unittest.TestCase):
    """Test del conteggio delle CPU."""

    def test_affinity(self):
        """Con sched_getaffinity conta le CPU assegnate al processo."""
        with patch.object(os, "sched_getaffinity", return_value={0, 1, 2}, create=True):
            self.assertEqual(tm.get_system_cpus(), 3)

    def test_affinity_error(self):
        """Se il sistema non risponde si usano 2 CPU."""
        with patch.object(os, "sched_getaffinity", side_effect=OSError, create=True):
            self.assertEqual(tm.get_system_cpus(), 2)

    def test_requested_capped(self):
        """Le CPU richieste non superano quelle disponibili."""
        for requested, expected in (("16", "4"), ("2+", "2")):
            with patch.object(tm, "get_system_cpus", return_value=4), patch.object(
                tm, "run_command"
            ) as run, patch.object(
                tm, "verify_build_output", return_value=False
            ), self.assertLogs(level="INFO"):
                result = tm.run_build(
                    "12345", "abcdef123456", tm.BuildOptions(cpus=requested)
                )
            self.assertTrue(result)
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[cmd.index("--cpus") + 1], expected)


class TestInstallFailure(unittest.TestCase):
    """Test dell'installazione di Docker quando un comando fallisce."""

    def test_exit_on_error(self):
        """Un comando fallito termina con codice 1."""
        with (
            patch.object(tm, "run_command", side_effect=FAILED),
            self.assertLogs(level="INFO"),
            self.assertRaises(SystemExit) as ctx,
        ):
            install_dependencies()
        self.assertEqual(ctx.exception.code, 1)


class TestClone(unittest.TestCase):
    """Test del clone del sorgente."""

    def test_existing_dir_skipped(self):
        """Se tdesktop esiste il clone non parte."""
        with in_temp_dir() as root, patch.object(tm, "run_command") as run:
            (root / "tdesktop").mkdir()
            with self.assertLogs(level="WARNING"):
                self.assertTrue(tm.clone_telegram_source())
            run.assert_not_called()

    def test_clone_ok(self):
        """Il clone usa il repository ufficiale con i submoduli."""
        with in_temp_dir(), patch.object(tm, "run_command") as run:
            with self.assertLogs(level="INFO"):
                self.assertTrue(tm.clone_telegram_source())
            run.assert_called_once_with(["git", "clone", "--recursive", tm.TDESKTOP_REPO])

    def test_clone_fails(self):
        """Un clone fallito restituisce False."""
        with (
            in_temp_dir(),
            patch.object(tm, "run_command", side_effect=FAILED),
            self.assertLogs(level="ERROR"),
        ):
            self.assertFalse(tm.clone_telegram_source())


class TestVerifyOutput(unittest.TestCase):
    """Test del controllo del binario compilato."""

    def test_missing_binary(self):
        """Binario assente: False."""
        with in_temp_dir(), self.assertLogs(level="WARNING"):
            self.assertFalse(tm.verify_build_output("non-esiste"))

    def test_binary_copied(self):
        """Il binario viene copiato in telegram_output/Telegram."""
        with in_temp_dir() as root:
            (root / "Telegram.bin").write_bytes(b"binario")
            with self.assertLogs(level="INFO"):
                self.assertTrue(tm.verify_build_output("Telegram.bin"))
            self.assertEqual((root / "telegram_output/Telegram").read_bytes(), b"binario")

    def test_copy_error_tolerated(self):
        """Se la copia fallisce il controllo resta positivo."""
        with in_temp_dir() as root, patch("shutil.copy2", side_effect=OSError("pieno")):
            (root / "Telegram.bin").write_bytes(b"binario")
            with self.assertLogs(level="WARNING"):
                self.assertTrue(tm.verify_build_output("Telegram.bin"))


class TestBuildImage(unittest.TestCase):
    """Test della build dell'immagine Docker."""

    INFO: ClassVar[dict] = {"Size": 2 * 1024**3, "Created": "ieri"}

    def build(self, force=False, exists=True, build_error=None):
        """Esegue build_docker_image con Docker simulato."""
        with patch("os.path.isdir", return_value=True), patch.object(
            tm, "docker_image_exists", return_value=exists
        ), patch.object(
            tm, "get_docker_image_info", return_value=self.INFO
        ), patch.object(
            tm, "_docker_build", side_effect=build_error
        ) as docker_build, self.assertLogs(level="INFO"):
            return tm.build_docker_image(force_rebuild=force), docker_build

    def test_missing_dockerfile_dir(self):
        """Senza la cartella del Dockerfile la build non parte."""
        with in_temp_dir(), self.assertLogs(level="ERROR"):
            self.assertFalse(tm.build_docker_image())

    def test_existing_image_reused(self):
        """Un'immagine già presente non viene ricostruita."""
        result, docker_build = self.build()
        self.assertTrue(result)
        docker_build.assert_not_called()

    def test_force_rebuild(self):
        """Con force_rebuild l'immagine viene ricostruita."""
        result, docker_build = self.build(force=True)
        self.assertTrue(result)
        docker_build.assert_called_once_with(
            "tdesktop:centos_env", "tdesktop/Telegram/build/docker/centos_env"
        )

    def test_missing_image_built(self):
        """Un'immagine assente viene costruita."""
        result, docker_build = self.build(exists=False)
        self.assertTrue(result)
        docker_build.assert_called_once()

    def test_unreadable_image_rebuilt(self):
        """Un'immagine senza metadati viene ricostruita."""
        with patch("os.path.isdir", return_value=True), patch.object(
            tm, "docker_image_exists", return_value=True
        ), patch.object(tm, "get_docker_image_info", return_value=None), patch.object(
            tm, "_docker_build"
        ) as docker_build, self.assertLogs(level="INFO"):
            self.assertTrue(tm.build_docker_image())
        docker_build.assert_called_once()

    def test_build_fails(self):
        """Una build fallita restituisce False."""
        result, _ = self.build(exists=False, build_error=FAILED)
        self.assertFalse(result)

    def test_docker_build_command(self):
        """Il comando docker build usa tag e percorso indicati."""
        with patch("os.path.isdir", return_value=True), patch.object(
            tm, "get_docker_image_info", return_value={"Size": 1, "Created": "oggi"}
        ), patch.object(tm, "run_command") as run, self.assertLogs(level="INFO"):
            self.assertTrue(tm.build_docker_image(force_rebuild=True))
        cmd = run.call_args.args[0]
        self.assertEqual(cmd[:2], ["docker", "build"])
        self.assertEqual(
            cmd[-3:],
            ["-t", "tdesktop:centos_env", "tdesktop/Telegram/build/docker/centos_env"],
        )


class TestRunBuild(unittest.TestCase):
    """Test della compilazione nel container."""

    @contextmanager
    def build_env(self, error=None):
        """Docker simulato per run_build; restituisce il comando e i log."""
        with patch.object(tm, "run_command", side_effect=error) as run, patch.object(
            tm, "get_system_cpus", return_value=8
        ), patch.object(tm, "verify_build_output", return_value=False), self.assertLogs(
            level="INFO"
        ) as logs:
            yield run, logs

    def test_invalid_credentials(self):
        """Credenziali non valide: nessun comando viene lanciato."""
        with self.build_env() as (run, _):
            result = tm.run_build("12; rm -rf /", "abcdef123456")
        self.assertFalse(result)
        run.assert_not_called()

    def test_command_and_limits(self):
        """Memoria, CPU e flag finiscono nel comando docker run."""
        options = tm.BuildOptions(
            memory_limit="8g", cpus="4", extra_flags="-DA=1 -DB=2"
        )
        with self.build_env() as (run, _):
            result = tm.run_build("12345", "abcdef123456", options)
        cmd = run.call_args.args[0]
        self.assertTrue(result)
        self.assertEqual(cmd[cmd.index("-m") + 1], "8g")
        self.assertEqual(cmd[cmd.index("--cpus") + 1], "4")
        self.assertIn("-DTDESKTOP_API_ID=12345", cmd)
        self.assertIn("-DTDESKTOP_API_HASH=abcdef123456", cmd)
        self.assertEqual(cmd[-2:], ["-DA=1", "-DB=2"])

    def test_credentials_masked(self):
        """Nei log compare solo il prefisso delle credenziali."""
        with self.build_env() as (_, logs):
            tm.run_build("12345", "abcdef123456")
            logged = "\n".join(logs.output)
        self.assertIn("API ID: 123***", logged)
        self.assertNotIn("12345", logged)
        self.assertNotIn("abcdef123456", logged)

    def test_docker_failure(self):
        """Un errore di docker run restituisce False."""
        with self.build_env(error=FAILED):
            result = tm.run_build("12345", "abcdef123456")
        self.assertFalse(result)


class TestPrompts(unittest.TestCase):
    """Test dei passaggi interattivi."""

    def test_download_source(self):
        """Risposta positiva: il sorgente viene clonato."""
        with patch.object(tm, "ask_yes_no", return_value=True), patch.object(
            tm, "clone_telegram_source", return_value=True
        ) as clone:
            tm.handle_source_download()
        clone.assert_called_once()

    def test_download_fails(self):
        """Clone fallito: uscita con codice 1."""
        with patch.object(tm, "ask_yes_no", return_value=True), patch.object(
            tm, "clone_telegram_source", return_value=False
        ), self.assertRaises(SystemExit):
            tm.handle_source_download()

    def test_patch_accounts(self):
        """Senza download si può cambiare il limite di account."""
        with patch.object(tm, "ask_yes_no", side_effect=[False, True]), patch(
            "builtins.input", return_value="7"
        ), patch.object(tm, "modify_max_accounts", return_value=True) as modify:
            tm.handle_source_download()
        modify.assert_called_once_with("7")

    def test_patch_accounts_fails(self):
        """Modifica fallita: uscita con codice 1."""
        with patch.object(tm, "ask_yes_no", side_effect=[False, True]), patch(
            "builtins.input", return_value="x"
        ), patch.object(tm, "modify_max_accounts", return_value=False), self.assertRaises(
            SystemExit
        ):
            tm.handle_source_download()

    def test_nothing_to_do(self):
        """Due risposte negative non fanno nulla."""
        with patch.object(tm, "ask_yes_no", return_value=False), patch.object(
            tm, "clone_telegram_source"
        ) as clone, patch.object(tm, "modify_max_accounts") as modify:
            tm.handle_source_download()
        clone.assert_not_called()
        modify.assert_not_called()

    def docker_build(self, answers, inputs):
        """Esegue handle_docker_build con risposte simulate."""
        options = tm.BuildOptions(memory_limit="4g", cpus="2", extra_flags="-DX=1")
        with patch.object(tm, "build_docker_image", return_value=True), patch.object(
            tm, "ask_yes_no", side_effect=answers
        ), patch("builtins.input", side_effect=inputs), patch.object(
            tm, "run_build", return_value=True
        ) as run_build:
            tm.handle_docker_build(force_rebuild=False, options=options)
        return run_build

    def test_build_with_defaults(self):
        """Senza opzioni avanzate restano i valori della riga di comando."""
        run_build = self.docker_build([False, True], ["111", "hash"])
        run_build.assert_called_once_with(
            "111",
            "hash",
            tm.BuildOptions(memory_limit="4g", cpus="2", extra_flags="-DX=1"),
        )

    def test_advanced_options(self):
        """Le opzioni avanzate sostituiscono solo i valori digitati."""
        run_build = self.docker_build([True, True], ["111", "hash", "8g", "", ""])
        run_build.assert_called_once_with(
            "111",
            "hash",
            tm.BuildOptions(memory_limit="8g", cpus="2", extra_flags="-DX=1"),
        )

    def test_build_cancelled(self):
        """Senza conferma la build non parte."""
        with self.assertLogs(level="INFO"):
            run_build = self.docker_build([False, False], ["111", "hash"])
        run_build.assert_not_called()

    def test_image_build_fails(self):
        """Immagine non costruita: uscita con codice 1."""
        with patch.object(
            tm, "build_docker_image", return_value=False
        ), self.assertRaises(SystemExit):
            tm.handle_docker_build(force_rebuild=False, options=tm.BuildOptions())

    def test_build_fails(self):
        """Build fallita: uscita con codice 1."""
        with patch.object(tm, "build_docker_image", return_value=True), patch.object(
            tm, "ask_yes_no", side_effect=[False, True]
        ), patch("builtins.input", side_effect=["111", "hash"]), patch.object(
            tm, "run_build", return_value=False
        ), self.assertRaises(SystemExit):
            tm.handle_docker_build(force_rebuild=False, options=tm.BuildOptions())


class TestMain(unittest.TestCase):
    """Test del flusso principale."""

    def run_main(self, answers, argv=("prog",)):
        """Esegue main con risposte simulate e passi sostituiti."""
        with patch("sys.argv", list(argv)), patch.object(
            tm, "setup_logging", return_value="build.log"
        ), patch.object(tm, "ask_yes_no", side_effect=answers), patch.object(
            tm, "install_dependencies"
        ) as install, patch.object(tm, "handle_source_download"), patch.object(
            tm, "handle_docker_build"
        ) as build, self.assertLogs(level="INFO"):
            tm.main()
        return install, build

    def test_full_flow(self):
        """Con due sì partono installazione e build con le opzioni date."""
        install, build = self.run_main(
            [True, True], ("prog", "--force-rebuild", "--memory", "8g", "--cpus", "6")
        )
        install.assert_called_once()
        build.assert_called_once_with(
            force_rebuild=True, options=tm.BuildOptions("8g", "6", "")
        )

    def test_everything_skipped(self):
        """Con due no non parte nulla."""
        install, build = self.run_main([False, False])
        install.assert_not_called()
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
