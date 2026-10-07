# Checklist tecnica NIS2

Questa checklist traduce in controlli tecnici alcuni temi dell'articolo 21
della direttiva NIS2 e della guida ENISA. Non costituisce una certificazione o
un parere legale: l'applicabilità dipende dall'entità, dal settore e dalla
trasposizione nazionale.

| Area | Controllo nel progetto | Evidenza |
| --- | --- | --- |
| Supply chain | Dependabot per pip, Docker e GitHub Actions; CodeQL attivo | `.github/dependabot.yml`, workflow CodeQL |
| Sviluppo sicuro | Test di validazione input e injection; review obbligatoria | `test_telegram_maker.py`, PR template |
| Accesso | API ID/hash raccolti interattivamente e mascherati nei log | `telegram_maker_multi.py` |
| Isolamento | Build Docker con utente non-root | `Dockerfile` |
| Incident handling | Policy di sicurezza e contatto di segnalazione | `SECURITY.md` |
| Continuità | Log di build e verifica dell'artefatto prodotto | `setup_logging`, `verify_build_output` |

Azioni residue: mantenere immagini base e toolchain aggiornati, firmare release
e verificare checksum/attestazioni degli artefatti prima della distribuzione.
