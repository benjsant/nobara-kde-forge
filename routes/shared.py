"""Etat partage entre les blueprints : task, logs, helpers."""
import os
import sys
import queue
import threading
import logging
import subprocess
from pathlib import Path

log_queue = queue.Queue(maxsize=1000)
current_task = {"running": False, "name": "", "progress": 0}
task_lock = threading.Lock()

_current_process = None
_process_lock = threading.Lock()

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Timeout des scripts d'installation, en secondes.
# Defaut : 2h (Nobara rolling release peut depasser 30 min).
# Surchargeable via env var NOBARAFORGEKDE_SCRIPT_TIMEOUT.
def _resolve_script_timeout():
    raw = os.environ.get("NOBARAFORGEKDE_SCRIPT_TIMEOUT", "7200")
    try:
        v = int(raw)
        return v if v > 0 else 7200
    except (ValueError, TypeError):
        return 7200

SCRIPT_TIMEOUT = _resolve_script_timeout()


class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            log_queue.put_nowait(self.format(record))
        except queue.Full:
            pass


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_DIR / "nobaraforgekde.log"), QueueHandler()]
)
logger = logging.getLogger("nobaraforgekde")


def log_info(msg):    logger.info(msg)
def log_success(msg): logger.info(f"[OK] {msg}")
def log_warn(msg):    logger.warning(f"[WARN] {msg}")
def log_error(msg):   logger.error(f"[ERROR] {msg}")


def notify_desktop(title, message=""):
    try:
        subprocess.run(
            ["notify-send", "-a", "NobaraForgeKDE", "-i", "dialog-information", title, message],
            capture_output=True, timeout=3
        )
    except Exception:
        pass


def update_task_status(name, running, progress=0):
    with task_lock:
        was_running = current_task["running"]
        current_task["name"] = name
        current_task["running"] = running
        current_task["progress"] = progress
    if was_running and not running and progress == 100:
        notify_desktop("Termine", name)


def set_current_process(proc):
    global _current_process
    with _process_lock:
        _current_process = proc


def cancel_current_task():
    """Tue le processus en cours."""
    global _current_process
    with _process_lock:
        if _current_process and _current_process.poll() is None:
            _current_process.kill()
            _current_process = None
            return True
        return False


def run_script(script_name):
    script_path = Path("scripts") / f"{script_name}.py"
    if not script_path.exists():
        script_path = Path("scripts") / script_name
        if not script_path.exists():
            log_error(f"Script introuvable : {script_name}")
            return False
    try:
        log_info(f"Lancement de {script_name}...")
        # Pour les scripts Python, on les invoque via `python -m scripts.<name>` :
        # Python charge alors scripts/__init__.py (qui configure sys.path) avant
        # d'executer le module, ce qui evite tout hack sys.path.insert duplicate.
        if script_path.suffix == ".py":
            module_name = f"scripts.{script_path.stem}"
            cmd = [sys.executable, "-m", module_name]
        else:
            cmd = ["bash", str(script_path)]

        # Ajoute la racine du projet au PYTHONPATH (double securite : pour les
        # scripts bash et au cas ou `-m` serait court-circuite).
        project_root = Path(__file__).resolve().parent.parent
        existing_pp = os.environ.get("PYTHONPATH", "")
        new_pp = str(project_root) + (os.pathsep + existing_pp if existing_pp else "")
        env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONPATH": new_pp}
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1, env=env
        )
        set_current_process(process)
        for line in process.stdout:
            line = line.rstrip('\n')
            if line.strip():
                log_info(line)
        process.wait(timeout=SCRIPT_TIMEOUT)
        set_current_process(None)
        if process.returncode == 0:
            log_success(f"Termine : {script_name}")
            return True
        if process.returncode is not None and process.returncode < 0:
            log_warn(f"Annule : {script_name}")
            return False
        log_error(f"Echec : {script_name} (code {process.returncode})")
        return False
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
        set_current_process(None)
        log_error(f"Timeout : {script_name} (>{SCRIPT_TIMEOUT}s)")
        return False
    except Exception as e:
        set_current_process(None)
        log_error(f"Erreur {script_name} : {e}")
        return False
