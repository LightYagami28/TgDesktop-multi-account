"""Validazione degli input e domande s/n."""
import logging


def validate_voip_count(voipn):
    """Valida il numero massimo di account."""
    if not voipn.isdigit():
        raise ValueError("Il numero di account deve essere un numero intero positivo.")
    count = int(voipn)
    if count <= 0:
        raise ValueError("Il numero di account deve essere positivo.")
    return str(count)


def validate_api_id(apiid):
    """Valida l'API ID di Telegram."""
    apiid = apiid.strip()
    if not apiid:
        raise ValueError("API ID non può essere vuoto.")
    if not apiid.isdigit():
        raise ValueError("API ID deve essere un numero intero.")
    return apiid


def validate_api_hash(apihash):
    """Valida l'API hash di Telegram."""
    apihash = apihash.strip()
    if not apihash:
        raise ValueError("API hash non può essere vuoto.")
    if not all(c.isalnum() for c in apihash):
        raise ValueError("API hash deve contenere solo caratteri alfanumerici.")
    return apihash


YES_ANSWERS = {"y", "yes", "s", "si", "sì"}
NO_ANSWERS = {"n", "no"}
ANSWERS = {**dict.fromkeys(YES_ANSWERS, True), **dict.fromkeys(NO_ANSWERS, False)}


def _read_answer(prompt, input_func):
    """Risposta in minuscolo senza spazi; a fine input (EOF) vale "n"."""
    try:
        return input_func(prompt).strip().lower()
    except EOFError:
        return "n"


def ask_yes_no(prompt, default=True, input_func=input):
    """Chiede una conferma s/n e restituisce True o False."""
    # Invio (risposta vuota) restituisce il default. Le risposte non valide
    # vengono richieste di nuovo. A fine input (EOF) restituisce False, così
    # nessuna azione parte senza una conferma.
    while True:
        answer = _read_answer(prompt, input_func)
        if not answer:
            return default
        if answer in ANSWERS:
            return ANSWERS[answer]
        logging.warning(
            "Risposta non valida: digitare y oppure n (Invio = %s).",
            "y" if default else "n",
        )
