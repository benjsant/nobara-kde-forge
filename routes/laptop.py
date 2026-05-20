"""Routes laptop : detection, TLP, monitoring, dock, thermique, checks."""
import json
import subprocess
import threading
from pathlib import Path

from flask import Blueprint, jsonify, request

from routes.shared import (
    current_task,
    log_error,
    task_lock,
    update_task_status,
)
from utils.laptop_detect import is_laptop

bp = Blueprint("laptop", __name__)

CONFIG = Path(__file__).parent.parent / "configs" / "laptop.json"


def _load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def _is_task_running():
    with task_lock:
        return current_task["running"]


def _run_in_thread(task_name, target, *args):
    """Lance une action laptop dans un thread daemon."""
    if _is_task_running():
        return jsonify(success=False, error="Une tache est en cours"), 409

    def wrapper():
        update_task_status(task_name, True, 0)
        try:
            target(*args)
            update_task_status(task_name, False, 100)
        except Exception as e:
            log_error(f"Erreur {task_name}: {e}")
            update_task_status(task_name, False, -1)

    t = threading.Thread(target=wrapper, daemon=True)
    t.start()
    return jsonify(success=True, message=f"Tache '{task_name}' demarree")


@bp.route("/api/laptop/detect")
def detect():
    detected, battery = is_laptop()
    return jsonify(is_laptop=detected, battery=battery)


@bp.route("/api/laptop/status")
def status():
    """Etat des composants laptop (TLP, monitoring, dock)."""
    try:
        r = subprocess.run(["systemctl", "is-active", "tlp.service"],
                           capture_output=True, text=True, timeout=5)
        tlp_active = r.stdout.strip() == "active"
    except Exception:
        tlp_active = False

    tlp_conf_exists = Path("/etc/tlp.d/01-nobaraforgekde.conf").exists()

    from utils import check_package_installed
    cfg = _load_config()
    monitoring_pkgs = []
    for pkg in cfg["monitoring"]["packages"]:
        monitoring_pkgs.append({
            "name": pkg["name"],
            "description": pkg["description"],
            "installed": check_package_installed(pkg["name"]),
        })

    dock_settings = []
    logind = Path("/etc/systemd/logind.conf")
    logind_content = logind.read_text() if logind.exists() else ""
    for key, target_val in cfg["dock"]["logind_settings"].items():
        current = None
        for line in logind_content.splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{key}="):
                current = stripped.split("=", 1)[1]
                break
        dock_settings.append({
            "key": key,
            "target": target_val,
            "current": current,
            "applied": current == target_val,
        })

    # Packages vendor-specific (ex: asusctl pour ASUS) — proposes uniquement si
    # le vendor DMI correspond et qu'une entree existe dans configs/laptop.json
    _, battery = is_laptop()
    vendor_id = battery.get("vendor_id", "")
    vendor_pkgs = []
    vendor_block = (cfg.get("vendor_specific") or {}).get(vendor_id, {})
    for pkg in vendor_block.get("packages", []):
        vendor_pkgs.append({
            "name": pkg["name"],
            "description": pkg["description"],
            "installed": check_package_installed(pkg["name"]),
        })

    return jsonify(
        tlp={"active": tlp_active, "configured": tlp_conf_exists},
        monitoring=monitoring_pkgs,
        dock=dock_settings,
        vendor={"id": vendor_id, "name": battery.get("vendor", ""), "packages": vendor_pkgs},
    )


@bp.route("/api/laptop/apply", methods=["POST"])
def apply_selection():
    data = request.get_json(silent=True) or {}
    want_tlp = data.get("tlp", False)
    want_monitoring = data.get("monitoring", [])
    want_dock = data.get("dock", [])
    want_vendor = data.get("vendor", [])

    if not want_tlp and not want_monitoring and not want_dock and not want_vendor:
        return jsonify(success=False, error="Rien a appliquer"), 400

    from scripts.laptop_setup import (
        configure_dock_selective,
        install_monitoring_selective,
        install_tlp,
        install_vendor_packages,
    )

    # Resolution du vendor pour la whitelist cote serveur
    _, battery = is_laptop()
    vendor_id = battery.get("vendor_id", "")

    def _apply():
        if want_tlp:
            install_tlp()
        if want_monitoring:
            install_monitoring_selective(want_monitoring)
        if want_dock:
            configure_dock_selective(want_dock)
        if want_vendor:
            install_vendor_packages(vendor_id, want_vendor)

    return _run_in_thread("Configuration laptop", _apply)


@bp.route("/api/laptop/thermal")
def thermal_status():
    from scripts.laptop_setup import get_thermal_status
    return jsonify(services=get_thermal_status())


@bp.route("/api/laptop/thermal/toggle", methods=["POST"])
def thermal_toggle():
    from scripts.laptop_setup import disable_service, enable_service
    data = request.get_json(silent=True) or {}
    svc = data.get("service", "")
    enable = data.get("enable", False)

    cfg = _load_config()
    allowed = [s["name"] for s in cfg["thermal"]["services"]]
    if svc not in allowed:
        return jsonify(success=False, error=f"Service non autorise: {svc}"), 400

    if enable:
        ok = enable_service(svc)
    else:
        ok = disable_service(svc)

    return jsonify(success=ok, service=svc, enabled=enable)


@bp.route("/api/laptop/checks")
def hardware_checks():
    from scripts.laptop_setup import run_checks
    live_only = request.args.get("live_usb", "false").lower() == "true"
    results = run_checks(live_usb_only=live_only)
    return jsonify(checks=results)
