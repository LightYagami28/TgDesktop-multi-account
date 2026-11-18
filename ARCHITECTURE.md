# Architecture

This repository builds a Telegram Desktop variant with multiple-account support. The documented workflow is a source patch and validation pipeline around an upstream `tdesktop/` checkout, followed by a Linux build in Docker and artifacts under `telegram_output/Telegram`.

```text
+--------------------------------------------------------------+
|                   telegram_maker_multi.py                    |
|       (CLI, Gestione istanze, Log Redaction & Confine)       |
+------------------------------+-------------------------------+
                               |
        +----------------------+----------------------+
        v                                             v
+-----------------------+             +-----------------------+
|     validation.py     |             |    source_patch.py    |
| (Validazione input,   |             | (Patch sorgenti       |
|  anti-path-traversal) |             |  limite account)      |
+-----------------------+             +-----------------------+
```

## Main components

- `telegram_maker_multi.py` coordinates the build workflow and user interaction.
- `build_helpers.py` contains build support routines.
- `source_patch.py` applies source changes to the upstream checkout.
- `validation.py` checks inputs and generated state.
- `test_telegram_maker.py` contains the Python unit tests.

| Modulo | File | Responsabilità |
|---|---|---|
| CLI / Core | `telegram_maker_multi.py` | Entrypoint principale, orchestrazione creazione profili, mascheramento credenziali nei log. |
| Validazione | `validation.py` | Validazione rigorosa parametri (VoIP count, API ID, API Hash) e confinamento cartelle (`_confined_log_path`). |
| Patching | `source_patch.py` | Applicazione modifiche ai file sorgente upstream di Telegram Desktop. |
| Test Suite | `test_telegram_maker.py` | Suite esaustiva di test unitari unittest (75/75 test passati). |

## Boundaries

The repository automates the build; it does not provide a hosted Telegram service. Build output and upstream source are generated inputs/outputs, not documentation sources. See `SPEC.md` for design decisions and status notes.
