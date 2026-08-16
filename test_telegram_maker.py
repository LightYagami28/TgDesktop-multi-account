import unittest
import sys
import os
from unittest.mock import patch, MagicMock
from io import StringIO

# Import the functions from the main script
sys.path.insert(0, os.path.dirname(__file__))
from telegram_maker_multi import (
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
        from telegram_maker_multi import modify_max_accounts

        with patch("os.path.isfile", return_value=False):
            result = modify_max_accounts("5")
            self.assertFalse(result)

    def test_modify_max_accounts_pattern_not_found(self):
        """Should handle missing pattern in file."""
        from telegram_maker_multi import modify_max_accounts

        test_content = "// No kMaxAccounts pattern here\nint some_other_value = 5;\n"

        with patch("os.path.isfile", return_value=True):
            with patch("builtins.open", unittest.mock.mock_open(read_data=test_content)):
                result = modify_max_accounts("10")
                self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
