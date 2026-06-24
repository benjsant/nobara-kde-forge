# API Reference

Référence complète des 47 endpoints REST de NobaraForgeKDE.

**Base URL** : `http://localhost:5000`

---

## Conventions

### Headers de sécurité requis

Pour toutes les requêtes :
- `Host` doit être `localhost[:5000]` ou `127.0.0.1[:5000]` (sinon **421**)

Pour les requêtes mutatives (POST/PUT/DELETE) :
- `Origin` **ou** `Referer` doit avoir un host autorisé (sinon **403**)

### Codes HTTP utilisés

| Code | Sens |
|---|---|
| 200 | OK |
| 400 | Bad request (paramètres invalides) |
| 403 | Cross-origin rejected ou pas d'Origin/Referer |
| 404 | Resource not found |
| 409 | Conflict — tâche déjà en cours |
| 421 | Host header non autorisé |
| 500 | Server error (avec `error` field dans le body JSON) |

### Format de réponse standard

```json
{
  "success": true | false,
  "error": "message si success=false",
  ... (autres champs spécifiques à l'endpoint)
}
```

---

## Sommaire des endpoints

| Catégorie | Endpoints |
|---|---|
| [Status & système](#status--système) | 4 |
| [Logs](#logs) | 3 |
| [Tâches](#tâches) | 2 |
| [Profils](#profils) | 8 |
| [Paquets optionnels](#paquets-optionnels) | 1 |
| [Exécution scripts](#exécution-scripts) | 2 |
| [Thèmes](#thèmes) | 2 |
| [Thème recommandé (legacy)](#thème-recommandé-legacy) | 2 |
| [KDE settings](#kde-settings) | 4 |
| [KDE backups](#kde-backups) | 4 |
| [Tweaks](#tweaks) | 7 |
| [System & firewall](#system--firewall) | 3 |
| [Plasma Login Manager](#plasma-login-manager) | 2 |
| [Outils Nobara](#outils-nobara) | 2 |
| [État / rollback](#état--rollback) | 4 |
| [App lifecycle](#app-lifecycle) | 1 |

**Total : 47 endpoints**

---

## Status & système

### `GET /api/status`

Status global de l'application — polling toutes les 5s par le frontend.

**Réponse** :
```json
{
  "checks": {
    "internet": true,
    "sudo": true,
    "python_version": true,
    "tools": { "kwriteconfig6": true, "dnf": true, ... },
    "disk_free_gb": 234.5,
    "timeshift": true,
    "power": { "on_battery": false, "capacity": 95, "status": "Full" } | null,
    "failed_services": 0
  },
  "packages": {
    "dnf": 19, "optional": 5, "flatpak": 3,
    "themes_gtk": 5, "themes_icons": 2, "themes_cursors": 3
  },
  "task": { "running": false, "name": "", "progress": 0 }
}
```

Cache TTL : 8s côté serveur.

---

### `GET /api/system/info`

Identité système Nobara détaillée — appelé une fois au load + sur "Rafraîchir".

**Réponse** :
```json
{
  "success": true,
  "info": {
    "os": { "name": "Nobara Linux", "version": "43 (KDE...)", "id": "nobara", "variant": "KDE..." },
    "kernel": {
      "release": "7.0.9-200.nobara.fc43.x86_64",
      "machine": "x86_64",
      "detected": true,
      "patches": ["CachyOS", "BORE", "NTSYNC", "PREEMPT_DYN"],
      "hz": 1000
    },
    "plasma": "6.6.4",
    "mesa": "26.1.0",
    "session": { "type": "wayland", "desktop": "KDE" },
    "security": {
      "lsm": ["capability", "lockdown", "yama", "apparmor", "bpf", "landlock"],
      "selinux": "disabled"
    },
    "gaming_sysctls": {
      "split_lock_mitigate": "0",
      "max_map_count": "16777216",
      "tcp_mtu_probing": "1",
      "swappiness": "100"
    },
    "btrfs_root": {
      "is_btrfs": true,
      "options": ["rw", "relatime", "compress=zstd:1", ...],
      "compress": "zstd:1",
      "subvol": "/@",
      "discard": "discard=async"
    },
    "zram": [{ "name": "zram0", "size_mb": 8191 }]
  }
}
```

Cache TTL : 30s côté serveur.

---

### `GET /api/system/firewall`

Status de firewalld.

**Réponse** :
```json
{
  "success": true,
  "enabled": true,
  "default_zone": "public",
  "output": "..."  // sortie de firewall-cmd --list-all
}
```

---

### `POST /api/system/firewall/enable` et `POST /api/system/firewall/disable`

Active ou désactive firewalld (`systemctl enable/disable --now firewalld`).

**Réponse** :
```json
{ "success": true, "message": "Pare-feu active" }
```

---

## Logs

### `GET /api/logs/stream`

**Server-Sent Events** stream. Le frontend l'ouvre avec `new EventSource('/api/logs/stream')`.

**Format SSE** :
```
data: 2026-05-27 14:32:11 [INFO] Profile gaming : 4 packages
data: 2026-05-27 14:32:12 [OK] steam installed
: keepalive

data: 2026-05-27 14:32:15 [WARN] flatpak ...
```

Keepalive toutes les ~1s pour empêcher la connexion de fermer.

---

### `GET /api/logs/history`

Retourne les dernières 300 lignes du fichier `logs/nobaraforgekde.log`.

**Réponse** :
```json
{ "lines": ["...", "...", ...] }
```

---

### `POST /api/logs/clear`

Vide la queue SSE en mémoire (ne touche pas au fichier disque).

**Réponse** :
```json
{ "success": true }
```

---

## Tâches

### `POST /api/task/cancel`

Annule la tâche en cours (SIGKILL au subprocess).

**Réponse** :
- `200` : `{"success": true}`
- `409` : `{"success": false, "error": "Aucune tache en cours"}`

---

### `POST /api/execute/<action>`

Lance un script d'installation. **Actions valides** : `dnf_install`, `dnf_remove`, `optional_install`, `flatpak_install`, `themes_install`, `external_install`.

**Body** : aucun.

**Réponse** :
- `200` : `{"success": true, "message": "Lancement de dnf_install"}`
- `400` : action inconnue
- `409` : tâche en cours

Le script est lancé via `python -m scripts.<action>` dans un thread séparé. Suivi via `/api/status` (`task.running`).

---

### `POST /api/execute/all`

⚠️ **Route héritée**, non appelée depuis l'UI actuelle. Lance la séquence complète : update système → DNF → optional → external → remove → flatpak → themes. Conservée pour scripting CLI.

---

## Profils

### `GET /api/profiles`

Liste tous les profils avec metadata.

**Réponse** :
```json
{
  "success": true,
  "gpu": "amd",
  "profiles": {
    "base": {
      "name": "Base", "description": "...", "icon": "wrench",
      "suggested": false, "locked": false,
      "counts": { "apt": 18, "flatpak": 2, "external": 0, "remove": 0, "total": 20 }
    },
    ...
  }
}
```

- `suggested: true` pour le profil correspondant au GPU détecté
- `locked: true` pour le profil GPU opposé (impossible à cocher dans l'UI sauf override)

Cache TTL : 60s.

---

### `GET /api/profiles/<slug>`

Détail d'un profil (tous ses paquets).

**Réponse** :
```json
{
  "success": true,
  "profile": {
    "name": "Gaming",
    "description": "...",
    "icon": "gamepad",
    "apt": [{"name": "steam", "description": "..."}, ...],
    "flatpak": [{"app": "com.heroic...", "description": "..."}, ...],
    "external": [],
    "remove": []
  }
}
```

`404` si profil inconnu.

---

### `POST /api/profiles/install`

Lance l'installation de profils. **C'est l'endpoint principal**.

**Body** :
```json
{
  "profiles": ["gaming", "dev"],
  "snapshot": true
}
```

**Réponse** :
- `200` : tâche démarrée en background
- `400` : liste manquante ou non-array
- `404` : profil inconnu
- `409` : tâche déjà en cours

---

### `POST /api/profiles/dry-run`

Aperçu sans installer.

**Body** : `{"profiles": ["gaming"]}`

**Réponse** :
```json
{
  "success": true,
  "dry_run": {
    "gaming": {
      "apt": [{"name": "steam", "description": "...", "status": "installed|to_install|duplicate"}, ...],
      "flatpak": [...],
      "external": [...],
      "remove": [...]
    }
  }
}
```

---

### `POST /api/profiles/preflight`

Analyse statique : conflits + warnings GPU.

**Body** : `{"profiles": ["gaming", "amd"]}`

**Réponse** :
```json
{
  "success": true,
  "summary": {
    "apt_to_install": 12,
    "apt_already_installed": 8,
    "flatpak_to_install": 5,
    "flatpak_already_installed": 1,
    "external_count": 0,
    "remove_count": 0
  },
  "apt_to_install": [{"name": "steam", "profiles": ["gaming"]}, ...],
  "flatpak_to_install": [...],
  "external": [...],
  "remove": [...],
  "conflicts": [
    {"package": "X", "installed_by": ["A"], "removed_by": ["B"]}
  ],
  "warnings": [
    "Profil NVIDIA selectionne mais GPU AMD detecte — risque de conflit."
  ],
  "gpu": "amd"
}
```

---

### `POST /api/profiles/install-custom`

Installation à la carte (sélection manuelle depuis la modale Detail).

**Body** :
```json
{
  "apt": [{"name": "steam", "description": "..."}, ...],
  "flatpak": [{"app": "com.X", "description": "..."}, ...],
  "external": [{"name": "X", "description": "...", "cmd": "bash -c '...'"}, ...],
  "remove": [{"name": "Y", "description": "..."}, ...]
}
```

Au moins une liste doit être non-vide (400 sinon).

---

### `POST /api/profiles/export`

⚠️ **Route héritée**. Le frontend fait l'export côté client (Blob + download). Cette route retourne juste les slugs envoyés.

---

### `POST /api/profiles/import`

Valide un JSON importé : sépare les slugs valides des invalides.

**Body** : `{"profiles": ["gaming", "inconnu"]}`

**Réponse** :
```json
{
  "success": true,
  "profiles": ["gaming"],
  "invalid": ["inconnu"]
}
```

---

## Paquets optionnels

### `GET /api/optional/list`

Liste les paquets de `configs/optional_install.json` avec statut `installed: true|false`.

---

## Thèmes

### `GET /api/themes/catalog`

Catalogue complet (GTK + icons + cursors + Kvantum) avec statut `installed: true|false` pour chaque.

**Réponse** :
```json
{
  "success": true,
  "catalog": {
    "gtk": [
      {"name": "Breeze", "name_to_use": "Breeze", "description": "...", "has_url": false, "installed": true},
      {"name": "Orchis-theme", "name_to_use": "Orchis-Dark", "description": "...", "has_url": true, "installed": false},
      ...
    ],
    "icon": [...],
    "cursor": [...],
    "kvantum": [...]
  }
}
```

---

### `POST /api/themes/install`

Installe un thème depuis git.

**Body** :
```json
{
  "type": "gtk" | "icon" | "cursor" | "kvantum",
  "name": "Sweet",
  "system": true
}
```

Si `system: true` → install dans `/usr/share` (sudo). Sinon dans `~/.themes`, `~/.icons`, etc.

**Réponse** :
- `200` : tâche démarrée
- `400` : type/name manquant ou sassc manquant pour GTK
- `404` : thème introuvable dans le catalogue
- `409` : tâche en cours

---

## Thème recommandé (legacy)

### `GET /api/theme/status` (legacy)

État de la config thème recommandée (Breeze Dark par défaut, défini dans `configs/theme_config_recommended.json`).

---

### `POST /api/theme/apply_recommended` (legacy)

Applique la config recommandée.

⚠️ Ces 2 endpoints sont hérités du minty_forge, non appelés par l'UI actuelle. Conservés pour rétrocompatibilité scripting.

---

## KDE settings

### `GET /api/kde/options`

Retourne tous les paramètres KDE courants + les thèmes disponibles.

**Réponse** :
```json
{
  "success": true,
  "themes": {
    "gtk": ["Adwaita", "Breeze", "Orchis-Dark", ...],
    "icon": ["breeze", "Papirus", "Tela", ...],
    "cursor": [...],
    "plasma": [...],
    "kvantum": [...]
  },
  "current": {
    "gtk_theme": "Breeze",
    "icon_theme": "breeze",
    "color_scheme": "BreezeDark",
    "cursor_theme": "breeze_cursors",
    "cursor_size": "24",
    ...
  }
}
```

---

### `POST /api/kde/apply`

Applique les paramètres KDE via `kwriteconfig6`.

**Body** :
```json
{
  "settings": {
    "gtk_theme": "Sweet",
    "color_scheme": "BreezeDark",
    "num_desktops": "4",
    "night_light_temp": "4500",
    "vrr_policy": "1",
    ...
  }
}
```

Validation : `num_desktops` (1-20), `night_light_temp` (1700-6500), `cursor_size` (24/32/36/48/64), `vrr_policy` (0/1/2).

**Réponse** : tâche async, suivre via `/api/status`.

---

### `POST /api/kde/dark-mode`

Bascule clair/sombre via `plasma-apply-colorscheme` (fallback `kwriteconfig6`).

**Body** : `{"dark": true}` ou `{"dark": false}`

---

## KDE backups

### `GET /api/kde/backups`

Liste les sauvegardes triées par date desc.

**Réponse** :
```json
{
  "success": true,
  "backups": [
    {
      "filename": "kde-20260527-143000-avant-experiences.tar.gz",
      "size": 12345,
      "mtime": 1716816600.0,
      "timestamp": "20260527-143000",
      "label": "avant-experiences"
    },
    ...
  ]
}
```

---

### `POST /api/kde/backups/create`

Crée un nouveau backup.

**Body** : `{"label": "avant-experiences"}` (optionnel, max 32 chars [A-Za-z0-9_-])

**Réponse** :
```json
{
  "success": true,
  "backup": {
    "filename": "kde-20260527-143000-avant-experiences.tar.gz",
    "path": "...",
    "files_count": 8,
    "files": ["kdeglobals", "kwinrc", ...],
    "size": 12345,
    "timestamp": "20260527-143000",
    "label": "avant-experiences",
    "pruned": 0
  }
}
```

`pruned` = nombre de vieilles sauvegardes supprimées (rétention 30 max).

---

### `POST /api/kde/backups/restore`

Restaure une sauvegarde.

**Body** : `{"filename": "kde-20260527-143000-avant-experiences.tar.gz"}`

**Réponse** :
```json
{
  "success": true,
  "restored": ["kdeglobals", "kwinrc", ...],
  "skipped": [],
  "count": 8
}
```

Sécurité : validation regex du filename + filtrage des membres tar contre whitelist + check `..`/chemin absolu. `_notify_kde_reload()` déclenché après extraction.

---

### `POST /api/kde/backups/delete`

Supprime une sauvegarde.

**Body** : `{"filename": "kde-20260527-143000.tar.gz"}`

---

## Tweaks

### `POST /api/tweaks/plasma/reset`

`kquitapp6 plasmashell` → clear `~/.cache/plasma*` → `kstart6 plasmashell` (détaché).

---

### `POST /api/tweaks/cache/clear`

Vide `~/.cache/{thumbnails,krunner,icon-cache.kcache,ksycoca6,plasma*}`.

**Réponse** :
```json
{
  "success": true,
  "freed_bytes": 12345678,
  "cleared": ["thumbnails", "krunner", "plasma_engine_potd", ...]
}
```

---

### `GET /api/tweaks/services`

Liste les services systemd whitelistés avec leur statut.

**Réponse** :
```json
{
  "success": true,
  "services": [
    {
      "name": "fstrim.timer",
      "description": "TRIM SSD hebdomadaire (longevite SSD)",
      "active": true, "enabled": true,
      "raw_active": "active", "raw_enabled": "enabled"
    },
    ...
  ]
}
```

`raw_active` peut être `"missing"` si le service n'est pas installé.

---

### `POST /api/tweaks/services/toggle`

Active ou désactive un service whitelisté.

**Body** : `{"name": "fstrim.timer", "enable": true}`

**Réponse** :
```json
{ "success": true } | { "success": false, "error": "Cache sudo expire — relancez l'app ou tapez `sudo -v`" }
```

`400` si service hors whitelist.

---

### `GET /api/tweaks/audio`

État audio actuel.

**Réponse** :
```json
{
  "success": true,
  "current_rate": 48000,
  "configured_rate": 48000,
  "allowed_rates": [44100, 48000, 96000, 192000],
  "bt_premium": false
}
```

`current_rate` = lu via `pw-metadata 0 clock.rate` (peut être `null` si PipeWire non démarré).
`configured_rate` = lu du drop-in NobaraForgeKDE (peut être `null` si jamais configuré).

---

### `POST /api/tweaks/audio/rate`

Change le sample rate PipeWire.

**Body** : `{"rate": 96000}`

**Réponse** :
```json
{ "success": true, "rate": 96000 }
| { "success": true, "rate": 96000, "warning": "Config OK mais redemarrage PipeWire requis" }
```

`400` si rate non dans `[44100, 48000, 96000, 192000]`.

Écrit `~/.config/pipewire/pipewire.conf.d/10-nobaraforgekde-rate.conf` (atomique tmp+replace), puis `systemctl --user restart pipewire pipewire-pulse wireplumber`.

---

### `POST /api/tweaks/audio/bt-codecs`

Active/désactive les codecs BT premium (LDAC, aptX-HD, AAC).

**Body** : `{"enable": true}` ou `{"enable": false}`

Crée/supprime `~/.config/wireplumber/wireplumber.conf.d/51-nobaraforgekde-bt-codecs.conf`.

---

## System & firewall

Voir [Status & système](#status--système).

---

## Plasma Login Manager

### `GET /api/sddm/status`

⚠️ **URL héritée** (gardée pour compat frontend). En réalité gère **plasma-login-manager**.

**Réponse** :
- Si `plasmalogin.service` actif :
  ```json
  {
    "success": true,
    "dm": "plasmalogin",
    "current": { "theme": "...", "cursor_theme": "...", "cursor_size": "...", "numlock": "..." },
    "themes": ["theme1", "theme2", ...]
  }
  ```
- Si `sddm.service` actif (legacy Nobara) :
  ```json
  {
    "success": false,
    "dm": "sddm",
    "warning": "SDDM detecte. Nobara/Fedora KDE 42+ utilise plasma-login-manager. Migration recommandee : ..."
  }
  ```

---

### `POST /api/sddm/sync`

Synchronise la config plasma-login-manager avec le bureau actuel.

Écrit `/etc/plasmalogin.conf.d/nobaraforgekde.conf` avec :
- `Theme/CursorTheme` = `kcminputrc/Mouse/cursorTheme` actuel
- `Theme/CursorSize` = `kcminputrc/Mouse/cursorSize`
- `General/Numlock` = `on`

**Réponse** :
```json
{
  "success": true,
  "dm": "plasmalogin",
  "applied": ["CursorTheme = breeze_cursors", "CursorSize = 24", "Numlock = on"],
  "errors": [],
  "warnings": []
}
```

---

## Outils Nobara

### `GET /api/nobara/tools`

Liste les outils Nobara natifs avec leur disponibilité.

**Réponse** :
```json
{
  "success": true,
  "tools": [
    {"id": "welcome", "cmd": "nobara-welcome", "name": "Nobara Welcome", "description": "...", "icon": "🏠", "available": true},
    {"id": "driver_manager", "cmd": "nobara-driver-manager", ..., "available": true},
    ...
  ]
}
```

7 outils whitelistés : `welcome`, `driver_manager`, `drive_mount_manager`, `codec_wizard`, `resolve_wizard`, `sync`, `updater`.

---

### `POST /api/nobara/launch/<tool_id>`

Lance un outil Nobara dans la session graphique (subprocess détaché).

**Réponse** :
- `200` : `{"success": true, "message": "Nobara Welcome lance"}`
- `404` : outil inconnu ou pas installé

---

## État / rollback

### `GET /api/state`

Vue de l'historique d'actions (cap à 500 entries).

**Réponse** :
```json
{
  "success": true,
  "summary": {
    "total_actions": 23,
    "successful": 20,
    "failed": 3,
    "rollbackable": 18,
    "last_action": {...},
    "state_file": "..."
  },
  "entries": [
    {
      "id": 23,
      "timestamp": "2026-05-27T14:30:00",
      "action": "dnf_install",
      "target": "steam",
      "success": true,
      "rollback_cmd": ["sudo", "dnf", "remove", "-y", "steam"],
      "metadata": {"description": "...", "profile": "gaming"}
    },
    ...
  ]
}
```

---

### `POST /api/state/rollback/last`

Annule la dernière action (exécute sa `rollback_cmd`).

**Réponse** :
- `200` : `{"success": true, "rolled_back": {...}}`
- `404` : aucune action à rollback
- `500` : rollback impossible (commande inverse manquante ou échec d'exécution)

---

### `POST /api/state/rollback/all`

Annule toutes les actions en ordre inverse. Saute celles sans `rollback_cmd` (ex: `external_install`).

**Réponse** :
```json
{
  "success": true,
  "rolled_back": [{...}, {...}],
  "skipped_count": 2
}
```

---

### `DELETE /api/state/clear`

Efface tout l'historique sans rollback.

**Réponse** : `{"success": true}`

---

## App lifecycle

### `POST /api/quit`

Arrête proprement le serveur Flask (envoie SIGTERM au process).

**Réponse** : `{"success": true, "message": "Arret en cours..."}`

Le handler SIGTERM nettoie le lockfile + sudoers temporaire (via le `trap cleanup EXIT` du bash launcher).

---

## Exemples curl

```bash
# Status
curl -H "Host: localhost:5000" http://localhost:5000/api/status

# Info système Nobara
curl -H "Host: localhost:5000" http://localhost:5000/api/system/info

# Liste profils
curl -H "Host: localhost:5000" http://localhost:5000/api/profiles

# Installer gaming + dev (avec snapshot)
curl -X POST \
     -H "Host: localhost:5000" \
     -H "Origin: http://localhost:5000" \
     -H "Content-Type: application/json" \
     -d '{"profiles":["gaming","dev"],"snapshot":true}' \
     http://localhost:5000/api/profiles/install

# Backup KDE
curl -X POST \
     -H "Host: localhost:5000" \
     -H "Origin: http://localhost:5000" \
     -H "Content-Type: application/json" \
     -d '{"label":"test"}' \
     http://localhost:5000/api/kde/backups/create

# Stream logs (SSE)
curl -N -H "Host: localhost:5000" http://localhost:5000/api/logs/stream
```

---

## Authentification

**Aucune** — l'app est mono-utilisateur et écoute sur `127.0.0.1` uniquement.

Le seul "auth" est le middleware anti-CSRF/Host check : un attaquant ne peut pas exploiter via DNS rebinding ou cross-origin POST. Voir [docs/SECURITY.md](SECURITY.md).
