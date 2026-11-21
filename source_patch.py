"""Patch the kMaxAccounts constant in the Telegram Desktop source tree."""

from __future__ import annotations

import logging
import os
import re
from typing import Final

from validation import validate_voip_count

logger: logging.Logger = logging.getLogger(__name__)

MAIN_DOMAIN_PATH: Final[str] = "tdesktop/Telegram/SourceFiles/main/main_domain.h"
MAX_ACCOUNTS_PATTERN: Final[str] = (
    r"static\s+constexpr\s+auto\s+kMaxAccounts\s*=\s*(\d+)\s*;"
)


def _patch_max_accounts(path: str, voipn: str) -> bool:
    """Replace the kMaxAccounts value in a source file.

    Args:
        path: Path of the header file to patch.
        voipn: Validated maximum number of accounts.

    Returns:
        ``True`` when the value was replaced, ``False`` when the pattern is absent.
    """
    with open(path, "rt", encoding="utf-8") as fin:
        content = fin.read()

    match = re.search(MAX_ACCOUNTS_PATTERN, content)
    if match is None:
        logger.error("Pattern kMaxAccounts non trovato in %s", path)
        logger.error("Controlla se il file è della versione corretta di Telegram")
        return False

    modified = re.sub(
        MAX_ACCOUNTS_PATTERN,
        f"static constexpr auto kMaxAccounts = {voipn};",
        content,
    )
    with open(path, "wt", encoding="utf-8") as fout:
        fout.write(modified)

    logger.info("✓ kMaxAccounts modificato: %s → %s", match.group(1), voipn)
    return True


def modify_max_accounts(voipn: str) -> bool:
    """Set kMaxAccounts in the Telegram Desktop source tree.

    Args:
        voipn: Raw user input for the maximum number of accounts.

    Returns:
        ``True`` when the patch was applied, ``False`` on missing file,
        invalid input or filesystem error.
    """
    if not os.path.isfile(MAIN_DOMAIN_PATH):
        logger.error("File non trovato: %s", MAIN_DOMAIN_PATH)
        return False

    try:
        validated = validate_voip_count(voipn)
    except ValueError:
        logger.exception("Numero di account non valido")
        return False

    try:
        return _patch_max_accounts(MAIN_DOMAIN_PATH, validated)
    except OSError:
        logger.exception("Errore modifica file")
        return False
