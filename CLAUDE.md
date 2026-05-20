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
  - Header `Host` doit être `localhost[:port]` ou `127.0.0.1[:port]` — bloque DNS rebinding (sinon 421).
  - Sur POST/PUT/DELETE : `Origin` ou `Referer` doit avoir un host autorisé — bloque CSRF cross-origin (sinon 403).
  - GET reste ouvert (favoris/refresh navigateur).
- **Sandbox des commandes user** ([utils/sandbox.py](utils/sandbox.py)) :
  - `bwrap` (bubblewrap) enveloppe les `cmd_user` des thèmes : filesystem read-only sauf `~/.themes`, `~/.icons`, `~/.local`, `~/.config` et le clone path. PID/UTS namespace isolés, network gardé.
  - **Non applicable** aux commandes avec `sudo` (escalade root casse le user namespace) — pour celles-là, **audit log** systématique : la commande complète est affichée + `looks_dangerous()` détecte patterns suspects (eval, `/dev/tcp`, fork bomb, `rm -rf /`, pipes `curl|bash`, etc.).
  - Fallback transparent si `bwrap` absent.

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
│   ├── legacy.py            # /api/install, /api/remove, /api/update, /api/tools-check
│   ├── profiles.py          # /api/profiles/*
│   ├── kde_settings.py      # /api/kde/* — kwriteconfig6/kreadconfig6 (remplace dconf.py de minty_forge)
│   ├── login_manager.py     # /api/sddm/* — config plasma-login-manager (DM par defaut Nobara/Fedora KDE 42+) ; warning si SDDM detecte. URL gardee en /api/sddm/* pour compat front
│   ├── system.py            # /api/system/* — firewalld (remplace ufw)
│   ├── themes.py            # /api/themes/*
│   ├── state_routes.py      # /api/state/* — rollback
│   ├── nobara_tools.py      # /api/nobara/* — detection + launch des outils Nobara natifs (welcome, driver-manager, etc.)
│   └── laptop.py            # /api/laptop/*
│
├── scripts/                 # Logique d'installation (appelés par les routes)
│   ├── __init__.py
│   ├── dnf_install.py       # Remplace apt_install.py
│   ├── dnf_remove.py        # Remplace apt_remove.py
│   ├── flatpak_install.py
│   ├── external_install.py
│   ├── optional_install.py
│   ├── profile_install.py
│   ├── themes_install.py
│   └── laptop_setup.py
│
├── utils/                   # Utilitaires
│   ├── subprocess_utils.py  # run_command, dnf_install/remove/update/upgrade, rpm -q
│   ├── state_manager.py     # Actions: ACTION_DNF_INSTALL, ACTION_DNF_REMOVE, rollback
│   ├── logging_utils.py     # Logger "NobaraForgeKDE"
│   ├── file_utils.py        # JSON, fichiers, ConfigManager
│   ├── validation.py        # Validation Pydantic des configs
│   ├── profile_loader.py    # Charge les profils depuis configs/profiles/
│   ├── theme_manager.py     # ThemeManager avec chemins KDE Plasma + Kvantum
│   └── laptop_detect.py     # Détection laptop via DMI/battery
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
│   ├── laptop.json
│   └── profiles/            # Profils d'installation (base, gaming, dev, etc.)
│       ├── base.json, gaming.json, dev.json, multimedia.json, office.json
│       ├── docker.json, distrobox.json, browsers.json, privacy.json
│       ├── vpn.json, system.json, amd.json, nvidia.json
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
    ├── test_schemas.py      # Validation Pydantic round-trip sur tous les configs
    └── test_app_smoke.py    # Boot Flask + ping endpoints
```

## Différences clés avec minty_forge

| Aspect | minty_forge (Mint/Cinnamon) | nobara_kde_forge (Nobara/KDE) |
|---|---|---|
| Gestionnaire de paquets | `apt` / `dpkg-query` | `dnf` / `rpm -q` |
| Desktop | Cinnamon (gsettings/dconf) | KDE Plasma (kwriteconfig6/kreadconfig6) |
| Fichiers config desktop | schémas dconf | `kdeglobals`, `kwinrc`, `plasmarc`, `kcminputrc`, `kscreenlockerrc` |
| Display manager | LightDM + slick-greeter (crudini) | plasma-login-manager (`/etc/plasmalogin.conf.d/`) — DM par defaut Nobara/Fedora KDE 42+, fork SDDM |
| Firewall | `ufw` | `firewalld` (`firewall-cmd`) |
| Inhibition veille | gsettings Cinnamon power | `qdbus` D-Bus PowerManagement |
| Mode sombre | gsettings derivation thème | `plasma-apply-colorscheme` |
| Thèmes supplémentaires | — | Plasma themes, Kvantum themes |
| Repos externes | PPA | COPR |
| Paquets VPN UI | `*-gnome` | `plasma-nm-*` |

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
- Détection vendor laptop via DMI (`sys_vendor`/`product_name`) → `vendor_id` normalisé (`asus`, `lenovo`, `dell`, `hp`, `msi`, `framework`, `acer`, `razer`, `other`). Section `vendor_specific.<id>.packages` dans [configs/laptop.json](configs/laptop.json) — actuellement asusctl/supergfxctl/rog-control-center pour ASUS

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
