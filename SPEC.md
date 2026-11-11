# SPEC: TgDesktop Multi-Account Builder

## Obiettivo

Lo script è finito quando, su Linux con Docker, compila un Telegram Desktop con
il numero massimo di account scelto (`kMaxAccounts`) senza dover preparare a
mano la toolchain, usando l'ambiente di build Docker del progetto originale, con
coverage 100%, SonarCloud A/A/A e zero avvisi nei test e nell'analisi.

## Stato attuale verificato

Letto dai file e provato il 2026-11-11, ramo `main`. Repo pubblico, licenza
Apache-2.0, fork di OpenTelegramFiles/TgDesktop-multi-account.

| Componente | Valore | File |
| --- | --- | --- |
| Python | testato in CI su 3.13, 3.14, 3.15; solo libreria standard | `.github/workflows/tests.yml`, `README.md` |
| Test | `unittest` (libreria standard), 29 test | `test_telegram_maker.py` |
| Immagine base Docker | CentOS Stream 9, `quay.io/centos/centos:stream9` con digest fissato; etichetta versione 1.3.0 | `Dockerfile` |
| actions/checkout | v7.0.1 (SHA) | `tests.yml`, `codeql-analysis.yml` |
| actions/setup-python | v7.1.0 (SHA) | `tests.yml` |
| github/codeql-action (init, analyze) | v4.39.3 (SHA) | `codeql-analysis.yml` |
| Dependabot | `pip`, `docker`, `github-actions` | `.github/dependabot.yml` |

Esito del 2026-11-11: `python -m unittest -q test_telegram_maker.py` esegue 29
test, tutti superati. Coverage di riga e rami misurata in locale (`coverage
7.17.2`): `validation.py` 100%, `source_patch.py` 68%, `telegram_maker_multi.py`
26%, totale (test inclusi) 58%. La coverage non è misurata in CI e non c'è
un'analisi SonarCloud (nessun `sonar-project.properties`).

Incongruenza corretta: il vecchio SPEC indicava `github/codeql-action` v4.39.1;
i workflow usano v4.39.3.

Il workflow di test esegue `python -m unittest -v test_telegram_maker.py` e
`python -m py_compile` sui tre moduli. La compilazione reale non è coperta da
test né da CI (troppo pesante).

## Architettura

Moduli, senza dipendenze di terzi: `telegram_maker_multi.py` (orchestrazione e
CLI), `validation.py` (controllo degli input, domande sì/no), `source_patch.py`
(patch di `kMaxAccounts`). Ogni azione esterna passa da `subprocess.run` con
liste di argomenti, senza shell.

| Funzione | Ruolo |
| --- | --- |
| `main` | analisi dei parametri (`argparse`) e orchestrazione |
| `ask_yes_no` | domanda `[Y/n]`, Invio sceglie il valore predefinito |
| `validate_voip_count`, `validate_api_id`, `validate_api_hash` | controllo degli input |
| `install_dependencies` | installazione di Docker CE con `sudo apt` |
| `clone_telegram_source` | ottenimento dei sorgenti |
| `modify_max_accounts` | patch di `kMaxAccounts` (`source_patch.py`) |
| `build_docker_image`, `run_build` | build dell'immagine e compilazione nel contenitore |
| `verify_build_output` | controllo e copia del binario |
| `setup_logging` | log su file e a video, protezione contro il path traversal |

Flusso:

1. `main` configura il log e stampa le informazioni di sistema.
2. Domanda: installare Docker? In caso positivo `install_dependencies`.
3. `handle_source_download`: clone, oppure, se i sorgenti esistono, patch
   facoltativa di `kMaxAccounts`.
4. Domanda: compilare con Docker? In caso positivo `handle_docker_build`: build
   dell'immagine `tdesktop:centos_env` (riusata salvo `--force-rebuild`),
   richiesta di API ID e hash, opzioni avanzate, `run_build`.
5. `run_build` esegue `docker run` montando la cartella corrente in
   `/usr/src/tdesktop`, poi `verify_build_output`.

Dati: nessun database. File: `tdesktop/` (sorgenti e log),
`telegram_output/Telegram` (binario). Non legge variabili d'ambiente; `DEBUG=1`
e `MAKEFLAGS` sono passate al contenitore. Il valore patchato è in
`tdesktop/Telegram/SourceFiles/main/main_domain.h` (`kMaxAccounts`).

Interfacce:

- Opzioni CLI (README): `--force-rebuild`, `--memory` (4g), `--cpus` (2),
  `--cmake-flags`, `--log-dir` (`tdesktop`, deve restare dentro la cartella
  corrente).
- Esterne: `docker`, `git`, `sudo`/`apt`, `curl`, GitHub
  (`telegramdesktop/tdesktop`), repository apt di Docker.
- `Dockerfile` alla radice: immagine di build CentOS Stream 9 rinforzata (utente
  non root, healthcheck).

## Requisiti funzionali

1. Il numero di account è validato prima di ogni azione. Accettazione: i test di
   `validate_voip_count` passano; valori fuori intervallo o non numerici sono
   rifiutati.
2. API ID e hash sono validati, mai salvati su disco e mascherati nei log.
   Accettazione: i test di `validate_api_id` e `validate_api_hash` (inclusi
   quelli contro l'injection) passano; il mascheramento nel log non ha un test
   dedicato (da scrivere).
3. Il valore `kMaxAccounts` è sostituito con il numero scelto; se lo schema nel
   sorgente cambia, lo script segnala l'errore. Accettazione: test su
   `source_patch.py` con file sintetico; con pattern assente il codice di
   ritorno è un errore e il log riporta «Pattern kMaxAccounts non trovato».
4. Docker CE è installato solo su richiesta e solo su Ubuntu/Debian.
   Accettazione: `install_dependencies` è invocata solo dopo risposta
   affermativa; i test `test_install_no_apt_key` e `test_source_signed` passano;
   il comportamento su altre distribuzioni è da verificare.
5. L'immagine `tdesktop:centos_env` è riusata se esiste. Accettazione: senza
   `--force-rebuild` il secondo avvio non ricostruisce l'immagine.
6. La compilazione rispetta i limiti di memoria e CPU. Accettazione: il comando
   costruito da `_docker_run_command` contiene `-m` e `--cpus` pari ai valori
   scelti (CPU limitate a quelle disponibili); test da scrivere.
7. Il binario risultante è copiato in `telegram_output/Telegram` e verificato.
   Accettazione: `verify_build_output` restituisce `False` se il binario manca e
   `True` se esiste (la copia è facoltativa e un errore di copia è solo
   segnalato); test da scrivere.
8. La cartella dei log non può uscire dalla cartella corrente. Accettazione:
   `--log-dir ../x` è rifiutato; test da scrivere.

## Requisiti non funzionali

- Sicurezza: nessun `shell=True`, solo liste di argomenti; API ID e hash mai
  salvati; `--log-dir` confinato; workflow con permessi minimi,
  `persist-credentials: false`, azioni fissate per SHA, CodeQL settimanale e
  sulle PR; immagine base fissata per digest. Segnalazioni: `SECURITY.md`.
- Prestazioni: la compilazione completa richiede molto tempo, almeno 4 GB di RAM
  e 5 GB di disco (README).
- Accessibilità: l'interfaccia è solo testuale; i messaggi usano frasi complete
  e non solo colori.
- Privacy/GDPR: lo script non raccoglie né trasmette dati; le credenziali
  Telegram restano locali.
- Qualità: coverage 100% (oggi 58% misurata), SonarCloud A/A/A e hotspot A, zero
  avvisi in test e `py_compile`, azioni e immagine base all'ultima versione
  (Dependabot).
- Compatibilità: solo Linux (`os.uname`); i messaggi e i log sono in italiano.

## Limiti noti

- L'installazione di Docker riguarda Ubuntu/Debian con il repository Ubuntu di
  Docker (chiave in `/etc/apt/keyrings`, codename da `/etc/os-release`).
- Il `Dockerfile` usa pacchetti Qt5: il passaggio a CentOS Stream 10 richiede di
  controllarne la disponibilità.
- La patch di `kMaxAccounts` dipende dal formato dei sorgenti a monte.
- Il clone non fissa un tag: la build segue il ramo principale a monte.
- La compilazione reale non è coperta da test né da CI.

## Roadmap

1. Aggiungere la misura di coverage in CI e un workflow SonarCloud
   (`sonar-project.properties`).
2. Portare `source_patch.py` e `telegram_maker_multi.py` al 100% di coverage con
   funzioni di sistema simulate (`subprocess.run`, `os.uname`).
3. Opzione per fissare tag o commit a monte.
4. Modalità non interattiva (API ID e hash da stdin o da file).
5. Traduzione in inglese dei messaggi.
6. Valutare CentOS Stream 10.

## Fuori ambito

- Distribuzione di binari di Telegram Desktop.
- Modifiche al client oltre a `kMaxAccounts`.
- Sistemi diversi da Linux.
- Rispetto dei termini d'uso di Telegram: responsabilità di chi esegue lo
  script.

## Decisioni aperte per il proprietario

- Introdurre la coverage obbligatoria in CI e SonarCloud su un progetto di
  questa dimensione.
- Fissare per impostazione predefinita un tag a monte, a costo di build non
  aggiornate.
- Tradurre messaggi e log in inglese.
- Passaggio dell'immagine a CentOS Stream 10.

## Come verificare

```bash
python3 -m unittest -v test_telegram_maker.py
python3 -m py_compile telegram_maker_multi.py validation.py source_patch.py
python3 -m coverage run --branch -m unittest test_telegram_maker.py && python3 -m coverage report -m
```

Il terzo comando richiede il pacchetto `coverage`. Per una prova completa della
compilazione: `python3 telegram_maker_multi.py` su una macchina Linux con Docker
(lunga e pesante).
