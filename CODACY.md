# Note Codacy

## Falsi positivi noti

- `dangerous-spawn-process-audit` in `command_runner.py`: la regola segnala
  `os.posix_spawn` quando il primo argomento non e' una stringa letterale.
  Qui il runner riceve sempre un `argv` di liste, valida che il primo elemento
  sia un percorso assoluto e non interpreta mai una shell. Non esiste flusso
  di dati testuale verso il comando: la segnalazione e' un'euristica a bassa
  confidenza (il metadata della regola indica `confidence: LOW`).

Le docstring del progetto sono in stile Google; `.prospector.yml` allinea
pydocstyle a quella convenzione invece di trasformare oltre cento docstring
gia' corrette.
