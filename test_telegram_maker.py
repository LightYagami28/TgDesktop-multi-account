"""Test di telegram_maker_multi."""
import unittest
from unittest.mock import patch

from telegram_maker_multi import (
    ask_yes_no,
    docker_apt_source,
    install_dependencies,
    modify_max_accounts,
    run_command,
    validate_voip_count,
    validate_api_id,
    validate_api_hash,
)


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

    def test_special_characters_rejected(self):
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

    def test_special_characters_rejected(self):
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

    def test_special_characters_rejected(self):
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

    def test_voip_injection_prevention(self):
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

    def test_api_id_injection_prevention(self):
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

    def test_api_hash_injection_prevention(self):
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

    def test_modify_max_accounts_file_not_found(self):
        """Should handle missing file gracefully."""

        with patch("os.path.isfile", return_value=False):
            result = modify_max_accounts("5")
            self.assertFalse(result)

    def test_modify_max_accounts_pattern_not_found(self):
        """Should handle missing pattern in file."""

        test_content = "// No kMaxAccounts pattern here\nint some_other_value = 5;\n"

        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", unittest.mock.mock_open(read_data=test_content)):
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
        with patch("shutil.which", return_value=None):
            with self.assertRaises(FileNotFoundError):
                run_command(["comando-inesistente"])


class TestDockerInstall(unittest.TestCase):
    """Test dell'installazione di Docker."""

    def test_source_line_is_signed_by_keyring(self):
        """La riga del repository usa il keyring dedicato."""
        line = docker_apt_source("noble", "amd64")
        self.assertIn("signed-by=/etc/apt/keyrings/docker.asc", line)
        self.assertIn("ubuntu noble stable", line)

    def test_install_uses_keyring_not_apt_key(self):
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


if __name__ == "__main__":
    unittest.main()
