"""Routes /api/nobara - detection et lancement des outils Nobara natifs.

Plutot que de dupliquer la logique (drivers, MAJ, tweaks), on expose les outils
deja installes sur Nobara via des boutons. Ils s'ouvrent dans la session de
l'utilisateur (pas en root) car Flask tourne en mode utilisateur.
"""
import os
import shutil
import subprocess
from flask import Blueprint, jsonify

from routes.shared import log_info, log_warn, log_error

bp = Blueprint("nobara_tools", __name__)

# Outils Nobara natifs whitelistes (Nobara 41+). Pas de PATH arbitraire — uniquement ces commandes.
# Verifies presents sur Nobara 43 KDE : /usr/bin/nobara-*
_TOOLS = [
    {
        "id": "welcome",
        "cmd": "nobara-welcome",
        "name": "Nobara Welcome",
        "description": "Premier lancement : Discord, Steam, drivers, presets HTPC/handheld",
        "icon": "🏠",
    },
    {
        "id": "driver_manager",
        "cmd": "nobara-driver-manager",
        "name": "Driver Manager",
        "description": "Gestion drivers : NVIDIA, asusctl, xpadneo (Xbox Elite BT), Broadcom, ROCm",
        "icon": "🎛️",
    },
    {
        "id": "drive_mount_manager",
        "cmd": "nobara-drive-mount-manager",
        "name": "Drive Mount Manager",
        "description": "Automount des partitions au demarrage (fstab GUI)",
        "icon": "💾",
    },
    {
        "id": "codec_wizard",
        "cmd": "nobara-codec-wizard",
        "name": "Codec Wizard",
        "description": "Installation des codecs multimedia proprietaires (h264, h265, etc.)",
        "icon": "🎬",
    },
    {
        "id": "resolve_wizard",
        "cmd": "nobara-resolve-wizard",
        "name": "Resolve Wizard",
        "description": "Diagnostic et resolution de problemes systeme courants",
        "icon": "🛟",
    },
    {
        "id": "sync",
        "cmd": "nobara-sync",
        "name": "Nobara Sync",
        "description": "Synchronisation des metadonnees de depots Nobara",
        "icon": "🔁",
    },
    {
        "id": "updater",
        "cmd": "nobara-updater",
        "name": "Nobara Updater",
        "description": "Mise a jour systeme (gere les quirks de version Nobara)",
        "icon": "⬆️",
    },
]


def _tool_available(cmd):
    return shutil.which(cmd) is not None


@bp.route('/api/nobara/tools')
def list_tools():
    """Liste les outils Nobara avec leur statut de disponibilite."""
    result = []
    for tool in _TOOLS:
        result.append({**tool, "available": _tool_available(tool["cmd"])})
    return jsonify({"success": True, "tools": result})


@bp.route('/api/nobara/launch/<tool_id>', methods=['POST'])
def launch_tool(tool_id):
    """Lance un outil Nobara dans la session de l'utilisateur (non-bloquant)."""
    tool = next((t for t in _TOOLS if t["id"] == tool_id), None)
    if tool is None:
        return jsonify({"success": False, "error": f"Outil inconnu : {tool_id}"}), 404

    if not _tool_available(tool["cmd"]):
        log_warn(f"Outil non installe : {tool['cmd']}")
        return jsonify({
            "success": False,
            "error": f"{tool['cmd']} non installe. Reinstallez Nobara ou : sudo dnf install {tool['cmd']}",
        }), 404

    try:
        # start_new_session=True detache le process du serveur Flask
        # stdin/out/err redirigees vers /dev/null pour ne pas polluer les logs Flask
        env = os.environ.copy()
        subprocess.Popen(
            [tool["cmd"]],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        log_info(f"Lance : {tool['cmd']}")
        return jsonify({"success": True, "message": f"{tool['name']} lance"})
    except Exception as e:
        log_error(f"Echec lancement {tool['cmd']} : {e}")
        return jsonify({"success": False, "error": str(e)}), 500
