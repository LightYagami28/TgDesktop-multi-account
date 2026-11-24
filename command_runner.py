"""Esegue comandi di sistema senza shell e senza risoluzione implicita.

Ogni comando viene passato come lista di argomenti separati: il nome
dell'eseguibile e gli argomenti non sono mai uniti in una stringa e nessuna
shell viene interpretata. L'eseguibile deve essere un percorso assoluto, quindi
non dipende da PATH: la whitelist e la convalida dei valori dinamici stanno nel
chiamante, qui si garantisce solo l'esecuzione sicura di cio' che arriva.
"""

from __future__ import annotations

import os
import selectors
import signal
import threading
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

DEVNULL = object()


class CommandError(Exception):
    """Un comando e' terminato con un codice diverso da zero."""

    def __init__(self, returncode: int, cmd: Sequence[str]) -> None:
        """Memorizza codice di uscita e comando che ha generato l'errore."""
        self.returncode = returncode
        self.cmd = tuple(cmd)
        super().__init__(f"comando terminato con codice {returncode}: {self.cmd[0]}")


class CommandTimeout(Exception):
    """Un comando ha superato il tempo massimo consentito."""

    def __init__(self, cmd: Sequence[str], seconds: float) -> None:
        """Memorizza il comando interrotto e il limite di tempo applicato."""
        self.cmd = tuple(cmd)
        self.seconds = seconds
        super().__init__(f"comando interrotto dopo {seconds}s: {self.cmd[0]}")


@dataclass
class CompletedCommand:
    """Risultato di un comando, equivalente ai campi usati dal builder."""

    args: list[str]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    chunks: dict[str, list[bytes]] = field(default_factory=dict, repr=False)

    def _text(self, stream: str) -> str:
        data = b"".join(self.chunks.get(stream, []))
        return data.decode("utf-8", errors="replace")


def _close(fd: int | None) -> bool:
    """Chiude un descrittore; restituisce False se era gia' chiuso."""
    if fd is None:
        return False
    try:
        os.close(fd)
    except OSError:
        return False
    return True


def _write(fd: int, payload: bytes) -> bool:
    """Scrive sulla pipe; restituisce False se il comando ha chiuso la stdin."""
    try:
        os.write(fd, payload)
    except BrokenPipeError:
        return False
    return True


def _signal(pid: int, sig: int) -> bool:
    """Invia un segnale; restituisce False se il processo e' gia' uscito."""
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return False
    return True


def _terminate(pid: int) -> int:
    """Termina il processo e restituisce il suo stato di uscita."""
    _signal(pid, signal.SIGTERM)
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            return status
        time.sleep(0.02)
    _signal(pid, signal.SIGKILL)
    _, status = os.waitpid(pid, 0)
    return status


def _wait(pid: int, timeout: float | None) -> int:
    """Attende il processo, interrompendolo allo scadere del timeout."""
    if timeout is None:
        _, status = os.waitpid(pid, 0)
        return status
    deadline = time.monotonic() + timeout
    while True:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            return status
        if time.monotonic() >= deadline:
            return _terminate(pid)
        time.sleep(0.02)


def _collect(readers: dict[int, list[bytes]]) -> None:
    """Legge le pipe finche' il figlio non le chiude, senza bloccarsi."""
    selector = selectors.DefaultSelector()
    for fd, sink in readers.items():
        selector.register(fd, selectors.EVENT_READ, sink)
    try:
        while selector.get_map():
            for key, _ in selector.select():
                data = os.read(key.fd, 65536)
                if data:
                    key.data.append(data)
                else:
                    selector.unregister(key.fd)
                    _close(key.fd)
    finally:
        for key in tuple(selector.get_map().values()):
            _close(key.fd)
        selector.close()


def _validate(argv: Sequence[str], input: bytes | str | None, text: bool) -> None:
    """Convalida gli argomenti prima di qualsiasi effetto collaterale."""
    if not argv or not isinstance(argv, (list, tuple)):
        raise ValueError("argv deve essere una lista non vuota")
    if not PurePosixPath(argv[0]).is_absolute():
        raise ValueError("l'eseguibile deve essere un percorso assoluto")
    if isinstance(input, str) and not text:
        raise TypeError("input str richiede text=True")
    if not isinstance(input, (str, bytes, type(None))):
        raise TypeError("input deve essere str, bytes o None")


def _configure_streams(
    actions: list[tuple[Any, ...]],
    readers: dict[int, list[bytes]],
    stdout: Any,
    stderr: Any,
    capture_output: bool,
) -> tuple[int | None, int | None]:
    """Prepara le pipe di output e restituisce i descrittori di lettura."""
    out_read = err_read = None
    for fd_no, target in ((1, stdout), (2, stderr)):
        if capture_output and target is None:
            read_fd, write_fd = os.pipe()
            readers[read_fd] = []
            if fd_no == 1:
                out_read = read_fd
            else:
                err_read = read_fd
            actions.append((os.POSIX_SPAWN_DUP2, write_fd, fd_no))
            _close(write_fd)
        elif target is DEVNULL:
            actions.append((os.POSIX_SPAWN_OPEN, fd_no, os.devnull, os.O_WRONLY, 0))
        elif target is not None:
            actions.append((os.POSIX_SPAWN_DUP2, target, fd_no))
    return out_read, err_read


def _spawn(
    argv: Sequence[str], actions: list[tuple[Any, ...]], env: Mapping[str, str] | None
) -> int:
    """Avvia il figlio con ``posix_spawn``: nessuna shell e argomenti separati.

    L'eseguibile e' gia' convalidato come percorso assoluto da ``_validate`` e
    proviene dalla whitelist del chiamante. Non si usa ``fork`` + ``execve``:
    ``posix_spawn`` riceve la lista di argomenti gia' separata e applica le
    redirezioni con ``file_actions``, senza interpretare stringhe e senza
    esporre API di esecuzione dinamica a dati provenienti dall'esterno.
    """
    child_env = dict(os.environ if env is None else env)
    return os.posix_spawn(argv[0], list(argv), child_env, file_actions=actions)


def _make_result(
    argv: Sequence[str],
    readers: dict[int, list[bytes]],
    out_read: int | None,
    err_read: int | None,
    returncode: int,
) -> CompletedCommand:
    """Costruisce il risultato decodificando i frammenti raccolti."""
    chunks = {
        "stdout": readers[out_read] if out_read is not None else [],
        "stderr": readers[err_read] if err_read is not None else [],
    }
    result = CompletedCommand(args=list(argv), returncode=returncode, chunks=chunks)
    result.stdout = result._text("stdout")
    result.stderr = result._text("stderr")
    return result


def run(
    argv: Sequence[str],
    *,
    check: bool = False,
    capture_output: bool = False,
    text: bool = False,
    input: bytes | str | None = None,
    stdout: Any = None,
    stderr: Any = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> CompletedCommand:
    """Avvia ``argv`` senza shell e ne restituisce il risultato.

    Args:
        argv: Eseguiibile assoluto seguito da argomenti separati.
        check: Solleva ``CommandError`` se il codice di uscita non e' zero.
        capture_output: Raccoglie stdout e stderr invece di ereditarli.
        text: Decodifica l'output raccolto come UTF-8.
        input: Dati da scrivere sulla stdin del comando.
        stdout: DEVNULL, ``None`` (eredita) o un descrittore di file.
        stderr: Come ``stdout``.
        env: Ambiente del figlio; ``None`` eredita quello corrente.
        timeout: Secondi massimi prima di terminare il comando.

    Returns:
        Il risultato con codice di uscita ed eventuale output.

    Raises:
        ValueError: Se argv e' vuoto o l'eseguibile non e' assoluto.
        CommandTimeout: Se il comando supera ``timeout``.
        CommandError: Se ``check`` e' vero e il comando fallisce.
    """
    _validate(argv, input, text)

    actions: list[tuple[Any, ...]] = []
    readers: dict[int, list[bytes]] = {}
    in_read = in_write = None
    out_read = err_read = None
    try:
        out_read, err_read = _configure_streams(
            actions, readers, stdout, stderr, capture_output
        )
        if input is not None:
            in_read, in_write = os.pipe()
            actions.append((os.POSIX_SPAWN_DUP2, in_read, 0))
        pid = _spawn(argv, actions, env)
    except BaseException:
        _close(in_write)
        for reader_fd in readers:
            _close(reader_fd)
        raise
    finally:
        # Il figlio ha una copia della stdin: il genitore chiude solo la sua.
        _close(in_read)

    if in_write is not None and input is not None:
        payload = input.encode("utf-8") if isinstance(input, str) else input
        # Se il comando chiude la stdin prima di leggerla, il suo codice di
        # uscita viene comunque valutato da ``check``.
        _write(in_write, payload)
        _close(in_write)

    # La raccolta deve partire prima dell'attesa: con output oltre la capacity
    # della pipe il figlio si bloccherebbe scrivendo e l'attesa non finirebbe.
    collector = None
    if readers:
        collector = threading.Thread(target=_collect, args=(readers,), daemon=True)
        collector.start()

    status = _wait(pid, timeout)
    if collector is not None:
        collector.join()

    returncode = os.waitstatus_to_exitcode(status)
    if timeout is not None and returncode < 0:
        raise CommandTimeout(argv, timeout)

    result = _make_result(argv, readers, out_read, err_read, returncode)
    if check and returncode != 0:
        raise CommandError(returncode, argv)
    return result
