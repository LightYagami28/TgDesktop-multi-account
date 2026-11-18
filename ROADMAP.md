# Roadmap

Stato al 2026-11-17.

This document summarizes candidate work and maintenance priorities recorded in [SPEC.md](SPEC.md). Items are proposals without release dates or delivery commitments; confirm them before planning.

## Obiettivi e Priorità

1. **Test di compatibilità con Python 3.14+**: mantenimento del 100% di test passati in CI senza dipendenze terze (75/75 test verdi).
2. **Quality Gate Codacy & SonarCloud Grade A**: zero vulnerabilità, zero code smell e CCN medio < 3.
3. **Automazione build binari**: generazione containerizzata deterministica di pacchetti aggiornati con l'ultima release upstream di Telegram Desktop.
4. **Isolamento delle sessioni**: hardening continuo dei percorsi dati e confinamento di sicurezza delle directory di log (`validation.py`).

## Current documented scope

The project builds a Linux Telegram Desktop variant from upstream source using Docker. Read [README](README.md) for current prerequisites and build invocation.

## Proposals recorded in SPEC

- Expand test coverage for `source_patch.py` and `telegram_maker_multi.py`.
- Consider adding a coverage gate and Sonar analysis.
- Keep the upstream version pin explicit and reviewed.
- Consider a non-interactive mode and English user-facing messages.
- Evaluate CentOS Stream 10 support.

## Fuori ambito

- Inclusione di dipendenze Python esterne a runtime (il nucleo resta pura libreria standard).

These proposals do not imply implementation or support today. The macOS/Linux platform alternatives in `SPEC.md` remain design questions unless the specification says otherwise.
