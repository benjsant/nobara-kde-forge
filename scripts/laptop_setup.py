#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Actions d'optimisation PC portable : TLP, monitoring, dock, thermique."""

import sys
import json
import subprocess
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import (
    check_package_installed, dnf_install, dnf_remove,
    run_sudo_command, run_command,
    info, success, warn, error,
    get_state_manager, ACTION_DNF_INSTALL, ACTION_DNF_REMOVE
)

CONFIG_FILE = Path(__file__).parent.parent / "configs" / "laptop.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# --- TLP ---

def install_tlp():
    """Installe TLP, supprime power-profiles-daemon si present, ecrit la config."""
    cfg = load_config()["tlp"]
    sm = get_state_manager()

    # Supprimer les conflits
    for pkg in cfg.get("remove_conflicts", []):
        if check_package_installed(pkg):
            info(f"Suppression du paquet en conflit : {pkg}")
            result = dnf_remove([pkg])
            sm.record(
                action=ACTION_DNF_REMOVE, target=pkg, success=result.success,
                rollback_cmd=["sudo", "dnf", "install", "-y", pkg],
            )

    # Installer TLP
    for pkg in cfg["packages"]:
        if check_package_installed(pkg):
            info(f"{pkg} deja installe.")
            continue
        info(f"Installation de {pkg}...")
        result = dnf_install([pkg])
        sm.record(
            action=ACTION_DNF_INSTALL, target=pkg, success=result.success,
            rollback_cmd=["sudo", "dnf", "remove", "-y", pkg],
        )
        if result.success:
            success(f"{pkg} installe.")
        else:
            error(f"Echec installation de {pkg}.")
            return

    # Ecrire la configuration TLP
    tlp_conf = cfg.get("config", {})
    if tlp_conf:
        info("Ecriture de la configuration TLP...")
        lines = [
            "# Configuration TLP generee par NobaraForgeKDE",
            "# Fichier : /etc/tlp.d/01-nobaraforgekde.conf",
            "",
        ]
        for key, val in tlp_conf.items():
            lines.append(f"{key}={val}")
        lines.append("")
        content = "\n".join(lines)

        run_sudo_command(["mkdir", "-p", "/etc/tlp.d"])
        tmp = "/tmp/nobaraforgekde_tlp.conf"
        Path(tmp).write_text(content)
        result = run_sudo_command(["cp", tmp, "/etc/tlp.d/01-nobaraforgekde.conf"])
        if result.success:
            success("Configuration TLP ecrite dans /etc/tlp.d/01-nobaraforgekde.conf")
        else:
            warn("Impossible d'ecrire la config TLP.")

    # Activer et demarrer TLP
    run_sudo_command(["systemctl", "enable", "tlp.service"])
    run_sudo_command(["systemctl", "start", "tlp.service"])

    # Masquer power-profiles-daemon pour eviter conflit
    run_sudo_command(["systemctl", "mask", "power-profiles-daemon.service"])

    success("TLP installe et configure.")


# --- Monitoring ---

def install_monitoring():
    """Installe les paquets de monitoring."""
    cfg = load_config()["monitoring"]
    sm = get_state_manager()

    for pkg_info in cfg["packages"]:
        name = pkg_info["name"]
        if check_package_installed(name):
            info(f"{name} deja installe.")
            continue
        info(f"Installation de {name} ({pkg_info['description']})...")
        result = dnf_install([name])
        sm.record(
            action=ACTION_DNF_INSTALL, target=name, success=result.success,
            rollback_cmd=["sudo", "dnf", "remove", "-y", name],
        )
        if result.success:
            success(f"{name} installe.")
        else:
            warn(f"Echec installation de {name}.")

    if check_package_installed("lm_sensors"):
        info("Detection automatique des capteurs (sensors-detect)...")
        run_sudo_command(["sensors-detect", "--auto"])

    success("Paquets de monitoring installes.")


def install_monitoring_selective(package_names):
    """Installe uniquement les paquets de monitoring selectionnes."""
    cfg = load_config()["monitoring"]
    sm = get_state_manager()

    pkg_map = {p["name"]: p["description"] for p in cfg["packages"]}

    for name in package_names:
        if name not in pkg_map:
            warn(f"Paquet inconnu : {name}, ignore.")
            continue
        if check_package_installed(name):
            info(f"{name} deja installe.")
            continue
        info(f"Installation de {name} ({pkg_map[name]})...")
        result = dnf_install([name])
        sm.record(
            action=ACTION_DNF_INSTALL, target=name, success=result.success,
            rollback_cmd=["sudo", "dnf", "remove", "-y", name],
        )
        if result.success:
            success(f"{name} installe.")
        else:
            warn(f"Echec installation de {name}.")

    if "lm_sensors" in package_names and check_package_installed("lm_sensors"):
        info("Detection automatique des capteurs (sensors-detect)...")
        run_sudo_command(["sensors-detect", "--auto"])

    success("Paquets de monitoring selectionnes traites.")


# --- Dock ---

def configure_dock():
    """Configure logind.conf pour un usage dock."""
    cfg = load_config()["dock"]
    settings = cfg.get("logind_settings", {})
    configure_dock_selective(list(settings.keys()))


def configure_dock_selective(setting_keys):
    """Configure uniquement les parametres logind selectionnes."""
    cfg = load_config()["dock"]
    all_settings = cfg.get("logind_settings", {})
    logind_conf = "/etc/systemd/logind.conf"

    info("Configuration logind.conf...")
    applied = []
    for key in setting_keys:
        if key not in all_settings:
            warn(f"Parametre inconnu : {key}, ignore.")
            continue
        val = all_settings[key]
        run_sudo_command([
            "sed", "-i",
            f"s/^#*{key}=.*/{key}={val}/",
            logind_conf,
        ])
        info(f"{key}={val}")
        applied.append(key)

    if applied:
        result = run_sudo_command(["systemctl", "restart", "systemd-logind"])
        if result.success:
            success(f"logind configure ({len(applied)} parametre(s)).")
        else:
            warn("logind.conf modifie mais restart logind echoue.")


# --- Vendor-specific (ASUS, etc.) ---

def install_vendor_packages(vendor_id, package_names):
    """Installe les paquets vendor-specific selectionnes (asusctl, etc.).
    package_names est valide contre la liste vendor_specific.<vendor_id>.packages
    pour eviter qu'un client envoie un paquet arbitraire."""
    if not vendor_id:
        warn("Vendor inconnu, paquets vendor ignores.")
        return

    cfg = load_config().get("vendor_specific", {}).get(vendor_id)
    if not cfg:
        warn(f"Aucune entree vendor_specific pour '{vendor_id}', ignore.")
        return

    sm = get_state_manager()
    allowed = {p["name"]: p["description"] for p in cfg.get("packages", [])}

    for name in package_names:
        if name not in allowed:
            warn(f"Paquet {name} pas dans la whitelist vendor '{vendor_id}', ignore.")
            continue
        if check_package_installed(name):
            info(f"{name} deja installe.")
            continue
        info(f"Installation de {name} ({allowed[name]})...")
        result = dnf_install([name])
        sm.record(
            action=ACTION_DNF_INSTALL, target=name, success=result.success,
            rollback_cmd=["sudo", "dnf", "remove", "-y", name],
            metadata={"vendor": vendor_id},
        )
        if result.success:
            success(f"{name} installe.")
        else:
            warn(f"Echec installation de {name}.")


# --- Thermique ---

def get_thermal_status():
    """Retourne l'etat de chaque service optionnel."""
    cfg = load_config()["thermal"]
    results = []
    for svc in cfg["services"]:
        name = svc["name"]
        try:
            r = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True, text=True, timeout=5,
            )
            active = r.stdout.strip() == "active"
        except Exception:
            active = False
        try:
            r = subprocess.run(
                ["systemctl", "is-enabled", name],
                capture_output=True, text=True, timeout=5,
            )
            enabled = r.stdout.strip() == "enabled"
        except Exception:
            enabled = False
        results.append({
            "name": name,
            "description": svc["description"],
            "active": active,
            "enabled": enabled,
        })
    return results


def disable_service(service_name):
    """Desactive et stoppe un service."""
    info(f"Desactivation de {service_name}...")
    run_sudo_command(["systemctl", "stop", service_name])
    result = run_sudo_command(["systemctl", "disable", service_name])
    if result.success:
        success(f"{service_name} desactive.")
    else:
        warn(f"Echec desactivation de {service_name}.")
    return result.success


def enable_service(service_name):
    """Reactive et demarre un service."""
    info(f"Reactivation de {service_name}...")
    run_sudo_command(["systemctl", "enable", service_name])
    result = run_sudo_command(["systemctl", "start", service_name])
    if result.success:
        success(f"{service_name} reactive.")
    else:
        warn(f"Echec reactivation de {service_name}.")
    return result.success


# --- Checks ---

def run_checks(live_usb_only=False):
    """Execute les diagnostics materiels."""
    cfg = load_config()["checks"]
    results = []
    for check in cfg:
        if live_usb_only and not check.get("live_usb", False):
            continue
        name = check["name"]
        cmd = check["cmd"]
        try:
            r = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=30,
            )
            output = (r.stdout.strip() or r.stderr.strip() or "(pas de sortie)")
        except subprocess.TimeoutExpired:
            output = "(timeout)"
        except Exception as e:
            output = f"(erreur : {e})"
        results.append({
            "name": name,
            "output": output,
            "live_usb": check.get("live_usb", False),
        })
    return results


def main():
    import sys as _sys
    if len(_sys.argv) < 2:
        info("Usage: laptop_setup.py <action>")
        info("Actions: tlp, monitoring, dock, checks, checks_live")
        return
    action = _sys.argv[1]
    if action == "tlp":
        install_tlp()
    elif action == "monitoring":
        install_monitoring()
    elif action == "dock":
        configure_dock()
    elif action == "checks":
        for r in run_checks():
            info(f"[{r['name']}] {r['output']}")
    elif action == "checks_live":
        for r in run_checks(live_usb_only=True):
            info(f"[{r['name']}] {r['output']}")
    else:
        error(f"Action inconnue : {action}")


if __name__ == "__main__":
    main()
