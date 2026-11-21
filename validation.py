"""Input validation and yes/no prompts for the Telegram Desktop builder."""

from __future__ import annotations

import logging
from collections.abc import Callable

logger: logging.Logger = logging.getLogger(__name__)

YES_ANSWERS: frozenset[str] = frozenset({"y", "yes", "s", "si", "sì"})
NO_ANSWERS: frozenset[str] = frozenset({"n", "no"})
ANSWERS: dict[str, bool] = {
    **dict.fromkeys(YES_ANSWERS, True),
    **dict.fromkeys(NO_ANSWERS, False),
}


def validate_voip_count(voipn: str) -> str:
    """Validate the requested maximum number of Telegram accounts.

    Args:
        voipn: Raw user input representing a positive integer.

    Returns:
        The canonical decimal representation of the count.

    Raises:
        ValueError: When the input is empty, non-numeric or not positive.
    """
    if not voipn.isdigit():
        raise ValueError("Il numero di account deve essere un numero intero positivo.")
    count = int(voipn)
    if count <= 0:
        raise ValueError("Il numero di account deve essere positivo.")
    return str(count)


def validate_api_id(apiid: str) -> str:
    """Validate a Telegram API ID.

    Args:
        apiid: Raw user input for the numeric API ID.

    Returns:
        The trimmed API ID.

    Raises:
        ValueError: When the value is empty or not entirely numeric.
    """
    value = apiid.strip()
    if not value:
        raise ValueError("API ID non può essere vuoto.")
    if not value.isdigit():
        raise ValueError("API ID deve essere un numero intero.")
    return value


def validate_api_hash(apihash: str) -> str:
    """Validate a Telegram API hash.

    Args:
        apihash: Raw user input for the hexadecimal API hash.

    Returns:
        The trimmed API hash.

    Raises:
        ValueError: When the value is empty or contains non-alphanumeric characters.
    """
    value = apihash.strip()
    if not value:
        raise ValueError("API hash non può essere vuoto.")
    if not all(char.isalnum() for char in value):
        raise ValueError("API hash deve contenere solo caratteri alfanumerici.")
    return value


def _read_answer(prompt: str, input_func: Callable[[str], str]) -> str:
    """Read an answer, treating end-of-input as a negative response.

    Args:
        prompt: Text shown to the user.
        input_func: Callable used to read input (injectable for tests).

    Returns:
        Lowercase stripped answer, or ``"n"`` when input is exhausted.
    """
    try:
        return input_func(prompt).strip().lower()
    except EOFError:
        return "n"


def ask_yes_no(
    prompt: str,
    default: bool = True,
    input_func: Callable[[str], str] = input,
) -> bool:
    """Ask for confirmation and return the user's decision.

    An empty answer returns *default*. Invalid answers are asked again.
    End-of-input always returns ``False`` so no action starts without consent.

    Args:
        prompt: Text shown to the user.
        default: Value returned when the user just presses Enter.
        input_func: Callable used to read input (injectable for tests).

    Returns:
        ``True`` for a positive answer, ``False`` otherwise.
    """
    while True:
        answer = _read_answer(prompt, input_func)
        if not answer:
            return default
        if answer in ANSWERS:
            return ANSWERS[answer]
        logger.warning(
            "Risposta non valida: digitare y oppure n (Invio = %s).",
            "y" if default else "n",
        )
