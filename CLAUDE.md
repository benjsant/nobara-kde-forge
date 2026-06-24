# NobaraForgeKDE

Outil d'automatisation post-installation pour **Nobara KDE** (Fedora-based, KDE Plasma).
Port du projet **minty_forge** (Linux Mint Cinnamon) adapté à l'écosystème Nobara/Fedora/KDE.

## Lancement

```bash
./nobaraforgeKDE.sh                           # Lance tout (uv sync, sudo, inhibit veille, Flask)
./nobaraforgeKDE.sh --uninstall               # Retire les fichiers systeme deposes (sudoers, conf DM, TLP)
uv sync && uv run python nobara_kde_forge.py  # Equivalent direct (sans bash launcher)

# Mode CLI (sans Flask)
uv run python nobara_kde_forge.py --list-profiles
uv run python nobara_kde_forge.py --profile gaming,dev
uv run python nobara_kde_forge.py --profile gaming --dry-run

# Tests
uv run --group dev pytest tests/
```

Interface web Flask sur `http://localhost:5000`.

### Variables d'environnement

- `NOBARAFORGEKDE_SCRIPT_TIMEOUT` : timeout (secondes) des scripts d'installation lances via `/api/execute/*`. Defaut : 7200 (2h).

### Packaging

Le projet a un layout "flat" : `routes/`, `scripts/`, `utils/`, `schemas/` sont des packages à la racine. `pyproject.toml` les déclare via `[tool.hatch.build.targets.wheel]`. `uv sync` installe le projet en éditable.

Les scripts dans `scripts/` sont invoqués depuis Flask via `python -m scripts.<name>` (charge `scripts/__init__.py` qui configure `sys.path`). Pour exécution CLI directe (`python scripts/X.py`), chaque script garde un fallback `if __package__ in (None, "")` pour rester autonome.

### CI

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) : matrix Python 3.10-3.13, `uv sync --group dev`, `compileall`, **ruff check**, pytest, `bash -n` sur le launcher, validation JSON.

### Securite

- **Lock file global** ([utils/lockfile.py](utils/lockfile.py)) : `$XDG_RUNTIME_DIR/nobaraforgekde.lock` (fallback `/tmp/`) contient le PID Flask. Au démarrage : si le PID est vivant → refus avec exit 2. Stale (PID mort) → écrasé. `atexit` retire le lock si PID match. Évite que deux UI se marchent dessus sur DNF lock / `data/state.json`.
- **Anti-CSRF / DNS-rebinding** ([utils/security.py](utils/security.py)) :
  - Header `Host` doit être `localhost[:port]` ou `127.0.0.1[:port]` - bloque DNS rebinding (sinon 421).
  - Sur POST/PUT/DELETE : `Origin` ou `Referer` doit avoir un host autorisé - bloque CSRF cross-origin (sinon 403).
  - GET reste ouvert (favoris/refresh navigateur).
- **Sandbox des commandes user** ([utils/sandbox.py](utils/sandbox.py)) :
  - `bwrap` (bubblewrap) enveloppe les `cmd_user` des thèmes : filesystem read-only sauf `~/.themes`, `~/.icons`, `~/.local`, `~/.config` et le clone path. PID/UTS namespace isolés, network gardé.
  - **Non applicable** aux commandes avec `sudo` (escalade root casse le user namespace) - pour celles-là, **audit log** systématique : la commande complète est affichée + `looks_dangerous()` détecte patterns suspects (eval, `/dev/tcp`, fork bomb, `rm -rf /`, pipes `curl|bash`, etc.).
  - Fallback transparent si `bwrap` absent.
- **Backup config KDE** ([utils/kde_backup.py](utils/kde_backup.py)) : whitelist stricte de 15 fichiers (`kdeglobals`, `kwinrc`, `plasmarc`, panel layout, raccourcis, Kvantum, etc.) dans `~/.local/share/nobaraforgekde/backups/`. Filename validé par regex `^kde-\d{8}-\d{6}(-label)?\.tar\.gz$`. À la restauration, chaque membre du tar est filtré contre la whitelist + check `..`/chemin absolu - defense en profondeur.

### Pre-commit

```bash
uv tool install pre-commit
pre-commit install
```

Hooks configurés ([.pre-commit-config.yaml](.pre-commit-config.yaml)) : trailing whitespace, EOF fixer, check-yaml/json, check-merge-conflict, ruff (lint + autofix), bashate, validation Pydantic des profils. `ruff-format` est commenté par défaut (génère beaucoup de diff cosmétique).

### Raccourci KDE

```bash
./packaging/install-desktop.sh                # Installe nobara-kde-forge.desktop dans ~/.local/share/applications/
./packaging/install-desktop.sh --uninstall    # Retire le raccourci
```

L'app apparaît ensuite dans le menu Plasma sous le nom "NobaraForgeKDE".

## Architecture

```
nobara_kde_forge/
├── nobaraforgeKDE.sh        # Script d'entrée bash (installe uv, sudo, inhibe veille, lance Flask)
├── nobara_kde_forge.py      # Point d'entrée Python (vérifie les pré-requis puis lance web_app)
├── web_app.py               # Application Flask, enregistre les blueprints
├── start.sh                 # Alias vers nobaraforgeKDE.sh
├── pyproject.toml           # Config uv/pip (Flask, Pydantic)
│
├── routes/                  # Blueprints Flask (API JSON + SSE logs)
│   ├── __init__.py          # Enregistrement des blueprints
│   ├── shared.py            # Logger SSE, fonctions communes, notify-send
│   ├── legacy.py            # /api/status (+ failed_services), /api/system/info, /api/execute/*, /api/theme/*
│   ├── profiles.py          # /api/profiles/*
│   ├── kde_settings.py      # /api/kde/* - kwriteconfig6/kreadconfig6 + /api/kde/backups/* (cycle backup KDE)
│   ├── login_manager.py     # /api/sddm/* - config plasma-login-manager (DM par defaut Nobara/Fedora KDE 42+) ; warning si SDDM detecte. URL gardee en /api/sddm/* pour compat front
│   ├── system.py            # /api/system/* - firewalld (remplace ufw)
│   ├── themes.py            # /api/themes/* - catalogues GTK/icon/cursor/kvantum
│   ├── state_routes.py      # /api/state/* - rollback
│   ├── nobara_tools.py      # /api/nobara/* - detection + launch des outils Nobara natifs (welcome, driver-manager, etc.)
│   └── tweaks.py            # /api/tweaks/* - reset plasmashell, vidage caches, services systemd, audio PipeWire/BT
│
├── scripts/                 # Logique d'installation (appelés par les routes)
│   ├── __init__.py
│   ├── dnf_install.py       # Remplace apt_install.py
│   ├── dnf_remove.py        # Remplace apt_remove.py
│   ├── flatpak_install.py
│   ├── external_install.py
│   ├── optional_install.py
│   ├── profile_install.py
│   └── themes_install.py
│
├── utils/                   # Utilitaires
│   ├── subprocess_utils.py  # run_command, dnf_install/remove/update/upgrade, rpm -q
│   ├── state_manager.py     # Actions: ACTION_DNF_INSTALL, ACTION_DNF_REMOVE, rollback
│   ├── logging_utils.py     # Logger "NobaraForgeKDE"
│   ├── file_utils.py        # JSON, fichiers, ConfigManager
│   ├── validation.py        # Validation Pydantic des configs
│   ├── profile_loader.py    # Charge les profils depuis configs/profiles/
│   ├── theme_manager.py     # ThemeManager avec chemins KDE Plasma + Kvantum
│   ├── security.py          # Anti-CSRF / anti-DNS-rebinding middleware Flask
│   ├── sandbox.py           # bwrap wrapper + detection patterns dangereux
│   ├── lockfile.py          # Lock file global (PID file + signal handlers)
│   ├── power.py             # Detection batterie (sysfs) -> warning UI
│   ├── kde_backup.py        # Backup/restore config KDE : tar.gz dans ~/.local/share/nobaraforgekde/backups/
│   ├── plasma_tweaks.py     # Reset plasmashell + clear caches (~/.cache/plasma*, thumbnails, krunner)
│   ├── services_manager.py  # Toggle services systemd whitelistes (fstrim/bluetooth/cups/sshd/firewalld)
│   ├── audio_tweaks.py      # PipeWire sample rate + codecs BT premium (drop-in user-level)
│   └── system_info.py       # Detection identite Nobara : kernel patches (CACHY/BORE/NTSYNC), LSM, btrfs, zram (cache 30s)
│
├── schemas/                 # Modèles Pydantic (distro-agnostic)
│   ├── __init__.py
│   ├── packages.py, flatpak.py, external.py, themes.py, profile.py
│
├── configs/                 # Fichiers JSON de configuration
│   ├── install.json         # Paquets RPM à installer
│   ├── remove.json          # Paquets RPM à supprimer
│   ├── flatpak.json         # Flatpaks à installer
│   ├── external_packages.json  # Paquets via repos externes (ex: VSCode via repo Microsoft)
│   ├── optional_install.json
│   ├── themes_gtk.json, themes_icons.json, themes_cursors.json
│   ├── theme_config_recommended.json  # Config thème par défaut (Breeze Dark)
│   ├── themes_kvantum.json  # Catalogue thèmes Kvantum (Catppuccin, Layan, KvDark)
│   └── profiles/            # Profils d'installation
│       ├── base.json, gaming.json, dev.json, multimedia.json, office.json
│       ├── docker.json, distrobox.json, browsers.json, privacy.json
│       ├── vpn.json, system.json, amd.json, nvidia.json
│       ├── communication.json  # Messageries chiffrees (Signal/Element/LocalSend/Discord)
│       ├── htpc.json        # Variant Steam-HTPC (Kodi, gamescope)
│       └── handheld.json    # Variant Handheld type Steam Deck (DeckyLoader via Tweak Tool)
│
├── web/                     # Frontend
│   ├── templates/index.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
│
└── tests/                   # Tests pytest
    ├── test_schemas.py            # Validation Pydantic round-trip sur tous les configs
    ├── test_app_smoke.py          # Boot Flask + ping endpoints
    ├── test_security.py           # Host/Origin/CSRF + lockfile (signaux SIGTERM)
    ├── test_sandbox.py            # bwrap wrapper + looks_dangerous patterns
    ├── test_power.py              # Detection batterie sysfs
    ├── test_kde_backup.py         # Cycle backup KDE + path traversal + tar malicieux
    ├── test_plasma_tweaks.py      # clear_caches + reset (mocke kstart6/kquitapp6)
    ├── test_services_manager.py   # Whitelist + parsing systemctl mocke
    ├── test_audio_tweaks.py       # Drop-in PipeWire/WirePlumber user-level
    └── test_system_info.py        # Parsing OS release/kernel patches/btrfs/zram + cache
```

## Différences clés avec minty_forge

| Aspect | minty_forge (Mint/Cinnamon) | nobara_kde_forge (Nobara/KDE) |
|---|---|---|
| Gestionnaire de paquets | `apt` / `dpkg-query` | `dnf` / `rpm -q` |
| Desktop | Cinnamon (gsettings/dconf) | KDE Plasma (kwriteconfig6/kreadconfig6) |
| Fichiers config desktop | schémas dconf | `kdeglobals`, `kwinrc`, `plasmarc`, `kcminputrc`, `kscreenlockerrc` |
| Display manager | LightDM + slick-greeter (crudini) | plasma-login-manager (`/etc/plasmalogin.conf.d/`) - DM par defaut Nobara/Fedora KDE 42+, fork SDDM |
| Firewall | `ufw` | `firewalld` (`firewall-cmd`) |
| Inhibition veille | gsettings Cinnamon power | `qdbus` D-Bus PowerManagement |
| Mode sombre | gsettings derivation thème | `plasma-apply-colorscheme` |
| Thèmes supplémentaires | - | Plasma themes, Kvantum themes |
| Repos externes | PPA | COPR |
| Paquets VPN UI | `*-gnome` | `plasma-nm-*` |

## Features post-port (au-dela du port minty_forge)

### Backup config KDE
Sauvegarde whitelistee (15 fichiers : kdeglobals, kwinrc, plasmarc, panel layout, raccourcis, Kvantum, etc.) en tar.gz horodate dans `~/.local/share/nobaraforgekde/backups/`. Etiquette optionnelle. Restauration verifie chaque membre du tar contre la whitelist (defense en profondeur). Routes `/api/kde/backups/{create,restore,delete,list}`. UI : section "Sauvegardes config bureau" sous KDE Settings.

### Tweaks rapides ([routes/tweaks.py](routes/tweaks.py))
Trois sous-blocs :
- **Reparation Plasma** : reset plasmashell (kquitapp6 → clear ~/.cache/plasma* → kstart6 detache), vidage caches generaux
- **Services systemd** : toggles pour `fstrim.timer`/`bluetooth`/`cups`/`sshd`/`firewalld` via `sudo -n systemctl` (whitelist stricte cote Python)
- **Audio** : sample rate PipeWire (44k/48k/96k/192k) + codecs BT premium (LDAC/aptX-HD/AAC). Drop-in user-level dans `~/.config/{pipewire,wireplumber}/.conf.d/` (pas de sudo).

### Panneau "Identite systeme Nobara" ([utils/system_info.py](utils/system_info.py))
Detecte au demarrage et affiche en pills colorees :
- OS + kernel + patches detectes (CachyOS/BORE/NTSYNC/PREEMPT_DYN via parsing `/boot/config-<kernel>`)
- Plasma + Mesa + session (Wayland/X11)
- LSM list (apparmor/landlock/bpf/...) + statut SELinux
- Sysctls gaming Nobara (`split_lock_mitigate`, `vm.max_map_count`, `tcp_mtu_probing`)
- Btrfs racine (subvol/compress/discard) + zram

Lecture pure (`/etc/os-release`, `/proc/mounts`, `/proc/swaps`, `/sys/kernel/security/lsm`, `sysctl`). Cache 30s. Route `/api/system/info`. Permet a l'utilisateur de **voir ce que Nobara fait deja**, evitant la duplication de tweaks.

### Indicateur "failed services" dans la status-bar
`systemctl --failed --no-legend` count → status item vert (0) ou rouge (≥1). Diagnostic immediat des units en erreur sans ouvrir un terminal.

### Catalogue Kvantum ([configs/themes_kvantum.json](configs/themes_kvantum.json))
4eme catalogue de themes (avec GTK/icones/curseurs). Install via git clone + `cp -r src/<variant> ~/.config/Kvantum/`. Routes themes etendues, theme manager deja compatible.

### Mesa freeworld (specifique Nobara/RPMFusion)
Profil `amd.json` utilise les variantes `-freeworld` (`mesa-vulkan-drivers-freeworld`, `mesa-va-drivers-freeworld`, `mesa-vdpau-drivers-freeworld`). Ces paquets incluent les codecs proprietaires (h264/h265/AV1/MPEG-2) retires des paquets standard pour raisons de brevets US. **Le paquet `mesa-vdpau-drivers` standard n'existe plus** dans les depots Nobara.

## Conventions

- Le champ `"apt"` dans les JSON profils contient en réalité des paquets **DNF/RPM** (nom hérité de minty_forge pour compatibilité de structure)
- Les routes KDE settings utilisent un `_SETTINGS_MAP` qui mappe chaque setting à un tuple `(fichier_kde, groupe, clé)`
- Le state manager utilise `ACTION_DNF_INSTALL` / `ACTION_DNF_REMOVE` pour le rollback
- Les logs SSE sont envoyés via `/api/logs` (même mécanisme que minty_forge)
- Le frontend communique avec les endpoints `/api/kde/*` (au lieu de `/api/dconf/*`) et `/api/sddm/*` (au lieu de `/api/greeter/*`). Le prefix `/api/sddm/*` est gardé pour compatibilité front mais l'implémentation cible plasma-login-manager
- Les routes `/api/sddm/status` et `/api/sddm/sync` détectent automatiquement le DM actif : si `plasmalogin.service` actif → gestion normale, si `sddm.service` actif → warning UI sans modification (la migration vers plasma-login-manager doit être faite à la main)
- `system_update()` ([utils/subprocess_utils.py](utils/subprocess_utils.py)) utilise `nobara-updater cli` si disponible (préserve les quirks de version Nobara) avec fallback `dnf check-update` + `dnf upgrade`
- Le sudoers temporaire `/etc/sudoers.d/nobaraforgekde` (NOPASSWD pour `firewall-cmd`) est créé au lancement et **supprimé à la fermeture** via le `trap cleanup EXIT` du launcher bash. `./nobaraforgeKDE.sh --uninstall` permet de nettoyer manuellement tout fichier système restant
- Snapshot timeshift optionnel avant `/api/profiles/install` : checkbox UI dans la section profils, visible uniquement si timeshift est dispo (`data.checks.timeshift`)
- **Fonctionnalité laptop archivée** : la gestion PC portable (TLP, monitoring, mode dock, thermique, asusctl) est isolée dans la branche [`archive/laptop`](https://github.com/benjsant/nobara-kde-forge/tree/archive/laptop). La forge reste un simple utilitaire d'installation de paquets. Seul ajout côté laptop : avertissement batterie ([utils/power.py](utils/power.py)) - l'UI affiche une bannière "branchez le secteur" si l'utilisateur est sur batterie au moment de lancer une install. Détection via `/sys/class/power_supply/`, retourne `null` pour les desktops (indicateur caché).

## Commandes utiles

```bash
# Vérifier la syntaxe Python
uv run python -m py_compile web_app.py
uv run python -c "import flask; print(flask.__version__)"

# Lancer manuellement
uv run python web_app.py

# Vérifier les paquets Fedora
rpm -q <package_name>
dnf search <keyword>
dnf info <package_name>
```

## Projet parent

Le code source de **minty_forge** (projet original) se trouve dans :
`/mnt/Data/Dev/dev_projet/projet_en_cours/minty_forge/`
