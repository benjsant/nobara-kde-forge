"""Lock file global : evite que deux instances de NobaraForgeKDE tournent
simultanement (sinon /api/execute/* en concurrence -> conflits DNF lock,
race sur state.json, etc.).

Strategie
---------
- Path : $XDG_RUNTIME_DIR/nobaraforgekde.lock (fallback /tmp/) — pid file
- Au demarrage : verifier si le PID stocke est vivant
  * vivant -> refuser, afficher PID et URL
  * mort (stale) -> ecraser
  * absent -> creer
- Au shutdown (atexit) : retirer le lock si le PID matche le notre

Note : on n'utilise pas fcntl.flock car le Flask main process re-execute
parfois sa boucle (debug mode, reloader). Le pid file est plus simple et
suffit a la garantie 'une seule UI active'.
"""
import atexit
import os
from pathlib import Path


class LockfileError(Exception):
    """Raised when another instance is detected as running."""

    def __init__(self, pid, lock_path):
        self.pid = pid
        self.lock_path = lock_path
        super().__init__(
            f"Une autre instance de NobaraForgeKDE tourne deja (PID {pid}). "
            f"Lock : {lock_path}"
        )


def _lock_path():
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(xdg) if xdg and Path(xdg).is_dir() else Path("/tmp")
    return base / "nobaraforgekde.lock"


def _pid_alive(pid):
    """True si le PID est encore vivant. Utilise os.kill(pid, 0)."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Le PID existe mais on n'a pas le droit de le signaler -> autre user
        return True
    return True


def acquire(force=False):
    """Acquiert le lock global. Leve LockfileError si une autre instance est detectee.

    `force=True` ecrase un lock existant (utile pour debug). Garde ce flag
    desactive en production.
    """
    path = _lock_path()
    if path.exists():
        try:
            content = path.read_text().strip()
            existing_pid = int(content) if content.isdigit() else 0
        except OSError:
            existing_pid = 0

        if existing_pid == os.getpid():
            # Re-acquire dans le meme process : ok (reloader Flask par exemple)
            return path

        if not force and _pid_alive(existing_pid):
            raise LockfileError(existing_pid, path)
        # Stale : on ecrase

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(os.getpid()))
    except OSError as e:
        raise LockfileError(0, path) from e

    atexit.register(_release_if_ours, path, os.getpid())
    return path


def _release_if_ours(path, our_pid):
    """Retire le lock seulement si on en est proprietaire (PID match)."""
    try:
        if not path.exists():
            return
        content = path.read_text().strip()
        if content.isdigit() and int(content) == our_pid:
            path.unlink()
    except OSError:
        pass


def release():
    """Force la liberation du lock (appelable manuellement)."""
    _release_if_ours(_lock_path(), os.getpid())
