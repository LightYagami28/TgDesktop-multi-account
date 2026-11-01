"""Patch di kMaxAccounts nel sorgente di Telegram Desktop."""
import logging
import os
import re

from validation import validate_voip_count


MAX_ACCOUNTS_PATTERN = r'static\s+constexpr\s+auto\s+kMaxAccounts\s*=\s*(\d+)\s*;'


def _patch_max_accounts(path, voipn):
    """Sostituisce il valore di kMaxAccounts nel file; False se il pattern manca."""
    with open(path, "rt", encoding="utf-8") as fin:
        content = fin.read()

    match = re.search(MAX_ACCOUNTS_PATTERN, content)
    if not match:
        logging.error("Pattern kMaxAccounts non trovato in %s", path)
        logging.error("Controlla se il file è della versione corretta di Telegram")
        return False

    modified_content = re.sub(
        MAX_ACCOUNTS_PATTERN, f'static constexpr auto kMaxAccounts = {voipn};', content
    )
    with open(path, "wt", encoding="utf-8") as fout:
        fout.write(modified_content)

    logging.info("✓ kMaxAccounts modificato: %s → %s", match.group(1), voipn)
    return True


def modify_max_accounts(voipn):
    """Imposta kMaxAccounts nel sorgente di Telegram Desktop."""
    main_domain_path = "tdesktop/Telegram/SourceFiles/main/main_domain.h"

    if not os.path.isfile(main_domain_path):
        logging.error("File non trovato: %s", main_domain_path)
        return False

    try:
        voipn = validate_voip_count(voipn)
    except ValueError as exc:
        logging.exception(str(exc))
        return False

    try:
        return _patch_max_accounts(main_domain_path, voipn)
    except OSError as exc:
        logging.exception("Errore modifica file: %s", exc)
        return False
