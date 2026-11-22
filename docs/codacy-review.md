# Revisione finding Codacy — TgDesktop-multi-account

Data: 2026-11-22. Fonte: API Codacy v3,
`gh/LightYagami28/TgDesktop-multi-account`.
Metodo: `POST .../issues/overview` e `POST .../issues/search` con cursori,
livelli Error/High/Warning/Info.

## Conteggi

| Livello | Totale |
| --- | ---: |
| High | 3 |
| Warning | 39 |
| Error | 1 |
| Info | 212 |
| **Totale** | **255** |
| belowThreshold | 255 |

## Falsi positivi accertati

- **`Semgrep_python.lang.security.audit.dangerous-spawn-process-audit`** —
  `command_runner.py:188`: `_spawn` usa `os.posix_spawn` con eseguibile
  convalidato come percorso assoluto, argomenti separati e `file_actions`, senza
  shell. Categoria nota come falso positivo: non ridefinire.
- **`Semgrep_python.lang.best-practice.sleep.arbitrary-sleep`** —
  `command_runner.py:97`: `time.sleep(0.02)` in un loop di polling con scadenza
  `time.monotonic() + 2`; non e' un'attesa arbitraria.
- **`Prospector_pydocstyle` (115)** — docstring mancanti o con convenzione
  diversa da quella attesa: tipo documentazionale.

## Finding reali

- `PyLintPython3_W0212` (24), `C0103` (19), `C0116` (8), `Prospector_pylint`
  (6): stile Python.
- `markdownlint_MD013` (22), `MD022` (8), `MD060` (5): formattazione
  documentazione.
- `Lizard_ccn-minor` (1), `nloc-minor` (1), `file-nloc-medium` (1):
  complessita'/lunghezza.

Nessuna modifica a configurazioni o soglie; nessuna soppressione.
