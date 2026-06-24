# Architecture

Vue d'ensemble technique de NobaraForgeKDE pour les contributeurs.


## Sommaire

1. [Stack technique](#stack-technique)
2. [Vue d'ensemble](#vue-densemble)
3. [Organisation des dossiers](#organisation-des-dossiers)
4. [Cycle de vie d'une instance](#cycle-de-vie-dune-instance)
5. [Flow d'une installation de profil](#flow-dune-installation-de-profil)
6. [Threading & concurrence](#threading--concurrence)
7. [État persistant](#état-persistant)
8. [Schémas Pydantic](#schémas-pydantic)
9. [Frontend Alpine.js](#frontend-alpinejs)
10. [Subprocess & shell safety](#subprocess--shell-safety)
11. [Décisions de design notables](#décisions-de-design-notables)


## Stack technique

| Couche | Technologie | Version |
|---|---|---|
| Backend | Python 3.10+ | 3.10 / 3.11 / 3.12 / 3.13 (CI matrix) |
| Framework web | Flask | 3.0+ |
| Validation | Pydantic | 2.0+ |
| Frontend | HTML + CSS + Vanilla JS + Alpine.js | Alpine 3.13.10 (CDN) |
| Templates | Jinja2 (intégré Flask) | - |
| Tests | pytest | 8.0+ |
| Lint | ruff | 0.8+ |
| Build | uv (Astral) | system DNF prioritaire |
| Distribution OS cible | Nobara Linux 41+ KDE | Fedora 41+ base |
| Desktop env | KDE Plasma | 6.x (commandes `kwriteconfig6`/`kreadconfig6`) |

Le projet est volontairement **léger en dépendances** : Flask + Pydantic. Pas d'ORM, pas de SQLite, pas de framework JS lourd. Toute la persistance est en JSON sur disque.


## Vue d'ensemble

```
                 ┌───────────────────────────────────────────────┐
                 │  Utilisateur (navigateur, localhost:5000)     │
                 └──────────────────┬────────────────────────────┘
                                    │ HTTP + SSE
                                    │
              ┌──────────────────── ▼ ─────────────────────┐
              │           Flask app (web_app.py)            │
              │                                             │
              │  Middleware sécurité (utils/security.py)    │
              │     - Host strict (anti DNS rebinding)      │
              │     - Origin/Referer sur POST (anti CSRF)   │
              │                                             │
              │  9 Blueprints (routes/)                     │
              │   ├─ legacy    : status, logs, execute      │
              │   ├─ profiles  : install profil, dry-run    │
              │   ├─ kde_settings : kwriteconfig + backup   │
              │   ├─ themes    : catalogue git              │
              │   ├─ tweaks    : plasma, services, audio    │
              │   ├─ system    : firewalld                  │
              │   ├─ login_manager : Plasma Login Mgr       │
              │   ├─ nobara_tools : welcome, drivers, etc.  │
              │   └─ state_routes : rollback                │
              └──────────────────┬──────────────────────────┘
                                 │
                ┌────────────────┴────────────────┐
                │                                 │
        ┌───────▼────────┐               ┌────────▼──────────┐
        │  utils/        │               │  scripts/         │
        │  - subprocess  │               │  - dnf_install    │
        │  - state_mgr   │               │  - dnf_remove     │
        │  - sandbox     │               │  - flatpak_install│
        │  - lockfile    │               │  - external_inst  │
        │  - kde_backup  │               │  - themes_install │
        │  - system_info │               │  - profile_install│
        │  - audio_tweaks│               └────────┬──────────┘
        │  - ...         │                        │
        └───────┬────────┘                        │
                │                                 │ subprocess
                │ subprocess                      ▼
                └──────────────────────┬─────────────────────┐
                                       │                     │
                              ┌────────▼──────┐    ┌─────────▼────────┐
                              │  System tools │    │  Package mgrs    │
                              │  - kwriteconfig│    │  - dnf/rpm      │
                              │  - systemctl  │    │  - flatpak      │
                              │  - timeshift  │    │  - git (themes) │
                              │  - sudo       │    └──────────────────┘
                              │  - bwrap      │
                              └───────────────┘
```


## Organisation des dossiers

```
nobara-kde-forge/
├── nobaraforgeKDE.sh           # Bash launcher (uv install via DNF, sudo cache, inhibit veille)
├── start.sh                    # Alias vers nobaraforgeKDE.sh
├── nobara_kde_forge.py         # Entry point Python (UI ou CLI)
├── web_app.py                  # Flask app + register_blueprints + lockfile.acquire
├── pyproject.toml              # Config uv, ruff, pytest, hatchling build
├── uv.lock                     # Dépendances pinned (committed)
│
├── routes/                     # Blueprints Flask (47 routes au total)
│   ├── __init__.py
│   ├── shared.py               # Logger SSE, task lock, run_script
│   ├── legacy.py               # /api/status, /api/system/info, /api/execute/*, /api/quit, /api/theme/*
│   ├── profiles.py             # /api/profiles/* (install, dry-run, preflight, export/import)
│   ├── kde_settings.py         # /api/kde/* (apply, options, dark-mode) + /api/kde/backups/*
│   ├── themes.py               # /api/themes/* (catalog, install)
│   ├── tweaks.py               # /api/tweaks/* (plasma, cache, services, audio)
│   ├── system.py               # /api/system/firewall* (firewalld)
│   ├── login_manager.py        # /api/sddm/* (Plasma Login Manager - alias hérité)
│   ├── nobara_tools.py         # /api/nobara/* (welcome, driver-manager, etc.)
│   └── state_routes.py         # /api/state/* (rollback)
│
├── scripts/                    # Scripts d'installation (appelés depuis routes/)
│   ├── __init__.py             # Configure sys.path pour python -m scripts.X
│   ├── dnf_install.py          # Lit configs/install.json + check_package_installed + dnf_install
│   ├── dnf_remove.py
│   ├── flatpak_install.py
│   ├── external_install.py     # Commandes bash arbitraires (avec audit log)
│   ├── optional_install.py
│   ├── profile_install.py      # Logic principale : install_profile(slug, seen_*, dry_run)
│   └── themes_install.py       # Pour le mode "thème recommandé" (mode CLI)
│
├── utils/                      # Modules utilitaires (16 fichiers)
│   ├── __init__.py             # Re-exports
│   ├── subprocess_utils.py     # run_command, dnf_install/remove/update, rpm -q (NO shell=True)
│   ├── state_manager.py        # StateManager (thread-safe, atomic write tmp+replace)
│   ├── logging_utils.py        # CLI logger (couleurs ANSI, utilisé en mode CLI)
│   ├── file_utils.py           # JSON helpers, ConfigManager
│   ├── validation.py           # Validation Pydantic des configs
│   ├── profile_loader.py       # Charge tous les profils depuis configs/profiles/
│   ├── theme_manager.py        # Détection + install thèmes (gtk/icon/cursor/plasma/kvantum)
│   ├── security.py             # register_security() : middleware anti-CSRF + Host check
│   ├── sandbox.py              # bwrap_available, wrap_user_command, looks_dangerous
│   ├── lockfile.py             # PID file + signal handlers (atexit ne couvre pas signaux)
│   ├── power.py                # Détection batterie (sysfs)
│   ├── kde_backup.py           # Backup/restore tar.gz config KDE
│   ├── plasma_tweaks.py        # Reset plasmashell + clear caches
│   ├── services_manager.py     # Whitelist + toggle systemd
│   ├── audio_tweaks.py         # PipeWire sample rate + WirePlumber BT codecs (drop-in)
│   └── system_info.py          # Détection Nobara : kernel patches, LSM, sysctls, btrfs, zram
│
├── schemas/                    # Modèles Pydantic strict
│   ├── __init__.py             # Re-exports
│   ├── packages.py             # Package, PackageList (DNF)
│   ├── flatpak.py              # FlatpakApp, FlatpakList
│   ├── external.py             # ExternalPackage, ExternalPackageList
│   ├── themes.py               # Theme, ThemeList
│   └── profile.py              # Profile (apt + flatpak + external + remove)
│
├── configs/                    # Fichiers JSON de configuration
│   ├── install.json            # Paquets DNF à installer (tab DNF)
│   ├── remove.json             # Paquets DNF à supprimer
│   ├── flatpak.json            # Flatpaks (tab Flatpak)
│   ├── external_packages.json  # Repos externes (VSCode via packages.microsoft.com)
│   ├── optional_install.json   # Paquets optionnels
│   ├── themes_gtk.json         # Catalogue thèmes GTK
│   ├── themes_icons.json       # Catalogue icônes
│   ├── themes_cursors.json     # Catalogue curseurs
│   ├── themes_kvantum.json     # Catalogue Kvantum
│   ├── theme_config_recommended.json  # (legacy, encore référencé)
│   └── profiles/               # 16 profils
│       ├── base.json, office.json, communication.json, gaming.json, htpc.json
│       ├── handheld.json, dev.json, multimedia.json, docker.json
│       ├── distrobox.json, browsers.json, privacy.json, vpn.json, system.json
│       ├── amd.json, nvidia.json
│
├── web/                        # Frontend
│   ├── templates/
│   │   └── index.html          # SPA single-page (~380 lignes)
│   └── static/
│       ├── css/style.css       # ~540 lignes, palette violet Nobara
│       └── js/app.js           # ~1750 lignes (mix vanilla + Alpine forge())
│
├── packaging/                  # Distribution
│   ├── nobara-kde-forge.desktop   # Entry KDE menu
│   ├── nobara-kde-forge.svg       # Icône
│   └── install-desktop.sh         # Installer/uninstaller du .desktop
│
├── tests/                      # ~85 tests pytest
│   ├── __init__.py
│   ├── test_schemas.py            # Round-trip Pydantic
│   ├── test_app_smoke.py          # Boot Flask + endpoints ping
│   ├── test_security.py           # Host/Origin/CSRF + lockfile (signaux SIGTERM)
│   ├── test_sandbox.py            # bwrap + looks_dangerous
│   ├── test_power.py              # Batterie sysfs
│   ├── test_kde_backup.py         # Cycle + path traversal + tar malicieux + retention
│   ├── test_plasma_tweaks.py      # clear_caches + reset mocké
│   ├── test_services_manager.py   # Whitelist + parsing systemctl mocké
│   ├── test_audio_tweaks.py       # Drop-in user-level + atomic write
│   └── test_system_info.py        # OS release / kernel / btrfs / zram + cache
│
├── docs/                       # Cette documentation
│   ├── USER_GUIDE.md
│   ├── ARCHITECTURE.md         (ce fichier)
│   ├── API.md
│   ├── SECURITY.md
│   ├── TROUBLESHOOTING.md
│   ├── CONTRIBUTING.md
│   └── CHANGELOG.md
│
├── data/                       # Runtime (gitignored)
│   └── state.json              # Historique actions pour rollback (cap 500)
├── logs/                       # Runtime (gitignored)
│   └── nobaraforgekde.log      # Rotating, 5 Mo × 4 backups
│
├── README.md                   # Vue d'ensemble publique
├── CLAUDE.md                   # Guide technique pour AI assistants
├── LICENSE                     # GPL-3.0
└── .github/workflows/ci.yml    # CI : matrix Python 3.10-3.13
```


## Cycle de vie d'une instance

### 1. Bash launcher (`nobaraforgeKDE.sh`)

```
1. Verifier Python 3
2. Installer uv (DNF → curl → pip, dans cet ordre)
3. uv sync (synchro deps dans .venv/)
4. sudo -v (cache passwd) + background renouvelle toutes les 50s
5. Installer sassc, git si absents
6. Créer /etc/sudoers.d/nobaraforgekde (NOPASSWD pour firewall-cmd) - auto-cleanup à la sortie
7. qdbus Inhibit (anti-veille)
8. trap cleanup EXIT (nettoyage)
9. uv run python nobara_kde_forge.py
```

### 2. Entry point Python (`nobara_kde_forge.py`)

```
1. Si --list-profiles  → list_all_profiles() + sortie
2. Si --profile X      → mode CLI : install_profile sans Flask
3. Sinon (mode UI) :
   a. check_env() : Python version, Flask/Pydantic dispos, outils KDE
   b. threading.Thread(target=open_browser, daemon=True) (timer 2s)
   c. subprocess.run([python, web_app.py])
```

### 3. Flask app (`web_app.py`)

```
1. Import des 9 blueprints
2. register_security(app, port=5000) - middleware AVANT blueprints
3. app.register_blueprint(...) × 9
4. main() :
   a. lockfile.acquire() - leve LockfileError si autre instance vivante
   b. install_signal_handlers() - SIGTERM/SIGINT nettoient le lock
   c. app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
```

### 4. Au runtime

```
- Threading=True : Flask peut servir plusieurs requêtes en parallèle
- SSE endpoint (/api/logs/stream) : long-running generator avec queue.Queue
- Status polling : frontend fetch /api/status toutes les 5s (Alpine.js setInterval)
- task_lock (threading.Lock) : empêche 2 installs concurrent (HTTP 409 sinon)
- _current_process (global) : référence au subprocess actif pour cancel via SIGKILL
```


## Flow d'une installation de profil

Exemple : utilisateur sélectionne `gaming` + `multimedia` et clique "Installer".

```
1. POST /api/profiles/install {profiles: ["gaming", "multimedia"], snapshot: true}
   → routes/profiles.py:install_profiles

2. Middleware sécurité (utils/security.py)
   - Host check : doit être localhost:5000 → OK
   - Origin/Referer check : doit avoir host autorisé → OK

3. Validation
   - get_profile("gaming"), get_profile("multimedia") → vérifie existence
   - 404 si profil inconnu

4. Acquisition du task lock
   with task_lock:
       if current_task["running"]:
           return 409  # tâche en cours
       current_task.update(running=True, name="Profils : gaming, multimedia")

5. Spawn thread + return 200 immédiatement
   threading.Thread(target=run, daemon=True).start()
   return {"success": True, "message": "Installation lancée"}

6. Dans le thread (run()):
   a. (Optionnel) timeshift_create_snapshot(...) si demandé
   b. dnf_update() - dnf check-update (pas upgrade)
   c. seen_apt, seen_flatpak, seen_external = set(), set(), set()
   d. Pour chaque profil dans l'ordre :
      install_profile(slug, seen_apt, seen_flatpak, seen_external)
        - Charge le profil via Pydantic (Profile.model_validate)
        - Pour chaque pkg.apt :
          * Si déjà dans seen_apt → skip
          * Si check_package_installed(pkg.name) → skip
          * dnf_install([pkg.name])
          * state.record(ACTION_DNF_INSTALL, pkg.name, success, ["sudo","dnf","remove","-y",pkg.name])
        - Pareil pour flatpak, external, remove (chacun avec son ACTION_* + rollback_cmd)
   e. update_task_status("Profils installés", running=False, progress=100)
   f. notify_desktop("Termine", "Profils installés") via notify-send

7. Le frontend voit la fin via polling /api/status (current_task running=false)
   - Re-active les boutons
   - Affiche toast "Profils installés"
```


## Threading & concurrence

### Threads existants

| Thread | Rôle | Daemon ? |
|---|---|---|
| Main (Flask) | Werkzeug serveur multithread | - |
| Worker (install profil) | Spawn par route, exécute le subprocess DNF/Flatpak | ✓ |
| SSE generator | Yield depuis `log_queue.get(timeout=1)` | (per-request) |
| Sudo keeper (bash) | `(while true; do sudo -n true; sleep 50; done)` | - |
| Browser opener | Délai 2s puis `webbrowser.open(URL)` | ✓ |

### Locks

- **`task_lock`** (threading.Lock) dans `routes/shared.py` - exclusivité d'une tâche d'installation
- **`_process_lock`** (threading.Lock) dans `routes/shared.py` - accès à `_current_process` (référence subprocess actif, pour cancel)
- **`StateManager._lock`** (threading.Lock) - accès aux entries du state
- **`_manager_lock`** (threading.Lock) - création singleton de StateManager

### Verrous inter-process

- **Lockfile** (`utils/lockfile.py`) : PID file dans `$XDG_RUNTIME_DIR/nobaraforgekde.lock`. Empêche 2 instances de NobaraForgeKDE. Détecte stale (PID mort) et écrase. Handlers SIGTERM/SIGINT nettoient (`atexit` ne couvre pas les signaux).

### Caches (variables module-level, sans lock)

- `_status_cache` (routes/legacy.py, TTL 8s)
- `_profiles_cache` (routes/profiles.py, TTL 60s)
- `_gpu_cache` (routes/profiles.py, populated une seule fois)
- `system_info._cache` (TTL 30s)

Pas de lock car les opérations dict.get/dict.set sont atomiques sous GIL CPython et les lectures concurrentes sont idempotentes (au pire double exécution de `gather()`).


## État persistant

| Donnée | Fichier | Format |
|---|---|---|
| Historique actions | `data/state.json` | JSON {version, next_id, entries[]} |
| Logs application | `logs/nobaraforgekde.log` | Plain text, rotation 5 MB × 4 |
| Sauvegardes config KDE | `~/.local/share/nobaraforgekde/backups/*.tar.gz` | Tar gzip, max 30 |
| Configs PipeWire user | `~/.config/pipewire/pipewire.conf.d/10-nobaraforgekde-*.conf` | spa-json |
| Configs WirePlumber | `~/.config/wireplumber/wireplumber.conf.d/51-nobaraforgekde-*.conf` | spa-json |
| Lock file | `$XDG_RUNTIME_DIR/nobaraforgekde.lock` | PID en texte |
| Sudoers temp (run-time) | `/etc/sudoers.d/nobaraforgekde` | Format sudoers |

### Écriture atomique (state.json + audio configs)

```python
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(content)
tmp.replace(path)  # rename atomique POSIX
```

Si crash entre write et replace : on garde l'ancien fichier intact.


## Schémas Pydantic

Tous les configs JSON sont validés par Pydantic v2 avec `extra='forbid'` (anti-typo).

```python
class Profile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

    name: str = Field(..., min_length=1)
    description: str = Field(default="")
    icon: str = Field(default="box")
    apt: list[ProfileAptPackage] = Field(default_factory=list)
    flatpak: list[ProfileFlatpak] = Field(default_factory=list)
    external: list[ProfileExternal] = Field(default_factory=list)
    remove: list[ProfileRemove] = Field(default_factory=list)

    @field_validator('icon')
    @classmethod
    def validate_icon(cls, v: str) -> str:
        if v not in VALID_ICONS:
            raise ValueError(f"Unknown icon '{v}'. Valid: {VALID_ICONS}")
        return v
```

### Validation Flatpak app_id

```python
app: str = Field(..., min_length=1, pattern=r'^[a-zA-Z0-9._-]+$')

@field_validator('app')
def validate_app_id(cls, v):
    if '.' not in v:
        raise ValueError(f"Invalid Flatpak app ID: '{v}'")
    return v
```

Conséquence : impossible d'avoir un fichier `configs/profiles/X.json` avec une typo qui passe silencieusement. Validation au démarrage de l'app + en CI via `test_schemas.py`.


## Frontend Alpine.js

L'UI est une **SPA single-page** (1 HTML, ~380 lignes) avec mix de :

1. **Vanilla JS** pour les sections non-migrées (profils, themes, history, logs, modal, etc.)
2. **Alpine.js** pour le status-bar et le panneau identité Nobara

### Composant Alpine `forge()`

```javascript
<body x-data="forge()" x-init="init()">
  ...
  <template x-for="item in checkItems" :key="item.id">
    <div class="status-item" :class="item.cls">
      <h3 x-text="item.label"></h3>
      <div class="value" x-text="item.value"></div>
    </div>
  </template>
  ...
</body>

<script>
function forge() {
  return {
    checks: {}, packages: {}, systemInfo: null,
    init() {
      this.updateStatus();
      this.loadSystemInfo();
      setInterval(() => this.updateStatus(), 5000);
    },
    async updateStatus() {
      const data = await (await fetch('/api/status')).json();
      this.checks = data.checks;
      this.packages = data.packages;
      window.dispatchEvent(new CustomEvent('status:updated', {detail: data}));
    },
    // ... 15 computed getters (osLabel, kernelLabel, etc.)
  };
}
</script>
```

Le code legacy (task bar, snapshot toggle, tools-warning) écoute l'event `status:updated` → pas de polling concurrent, et migration progressive possible.

### Pourquoi pas Vue/React ?

- Surdimensionné pour 5 sections d'UI réglages
- Pas de build step (déploiement = `git clone && launch`)
- Apprentissage zero pour qui sait du JS standard
- HTML reste lisible (les bindings sont des attributs, pas du JSX)

### CSS

Palette **violet Nobara** (#9b59b6 primary, #7d3c98 secondary). Tout via CSS variables :
- `--primary, --secondary, --danger, --warning, --success, --dark, --light, --bg, --card-bg, --card-shadow, --text, --text-muted, --border`
- Variant dark mode via `[data-theme="dark"]` selector

Limites connues : ~63 styles inline dans le HTML, ~82 dans des innerHTML JS → candidat à un cleanup (extraction en classes utilitaires).


## Subprocess & shell safety

### Règle d'or : jamais `shell=True`

Tous les appels passent par `utils.subprocess_utils.run_command([list, of, args])` qui wrappe `subprocess.run()` sans `shell=True`. Pas d'injection possible via interpolation de string.

### Exceptions contrôlées

Les `configs/profiles/*.json` peuvent contenir des commandes `external.cmd` qui sont des **strings bash** (ex: Docker repo setup). Elles sont :

1. Exposées dans l'audit log (toute la commande affichée)
2. Scannées par `looks_dangerous()` qui détecte 11 patterns suspects (eval, /dev/tcp, curl|bash, fork bomb, rm -rf /, dd vers /dev/*, etc.)
3. Exécutées via `["bash", "-c", cmd]` (toujours sans `shell=True`)

### Commandes user-level → bwrap sandbox

Les `cmd_user` des thèmes (install.sh post-clone) sont enveloppées dans `bwrap` quand dispo :

```python
bwrap --ro-bind / /     # FS read-only
     --proc /proc
     --dev /dev
     --tmpfs /tmp
     --unshare-user-try
     --unshare-pid
     --unshare-uts
     --die-with-parent
     --new-session
     --share-net
     --bind ~/.themes ~/.themes   # writable paths
     --bind ~/.icons ~/.icons
     ...
     bash -c "<install command>"
```

Fallback transparent si `bwrap` absent.

### sudo

- `sudo -n` partout (no-prompt). Si cache expiré → échec propre.
- Sudoers temporaire `/etc/sudoers.d/nobaraforgekde` créé par le launcher uniquement pour `firewall-cmd`. Auto-cleanup à `EXIT`.
- Toutes les autres commandes sudo utilisent le cache de session (renouvelé toutes les 50s par le launcher).


## Décisions de design notables

### Pourquoi Flask, pas FastAPI ?

- Plus simple, moins de magie ASGI
- Pas besoin d'async (le code est IO-bound mais pas concurrent au point de saturer)
- Werkzeug en multithread suffit pour 1 utilisateur local

### Pourquoi JSON pour les configs, pas YAML/TOML ?

- Standard universel, parseur dans stdlib
- Validation Pydantic native
- Pas d'ambiguïté de syntaxe (TOML/YAML peuvent piéger)

### Pourquoi `kwriteconfig6` plutôt que toucher les .desktop direct ?

- Notifications KGlobalSettings automatiques (Plasma recharge en live)
- Atomic au niveau du fichier (gérée par Plasma)
- Plus robuste aux changements de structure dans `kdeglobals` (Plasma 6.7+ pourrait réorganiser)

### Pourquoi un sudoers temporaire ?

- `firewall-cmd` est appelé fréquemment (status check à chaque load)
- Sans NOPASSWD : prompt password à chaque interaction → UX cassée
- Limité à `/usr/bin/firewall-cmd` (pas un sudoers global) + auto-cleanup
- Le risque résiduel est minime (un local user qui a déjà sudo pourrait le faire)

### Pourquoi un lockfile via PID, pas `fcntl.flock` ?

- Flask en mode debug fait des reloads avec `os.exec()` qui invalide le flock du parent
- PID file + check `os.kill(pid, 0)` est plus simple et marche dans tous les cas
- Stale lock detection (PID mort) géré explicitement

### Pourquoi le state.json a un cap (500 entries) ?

- Sans cap, l'historique grossit indéfiniment (1 entry par paquet installé)
- Au-delà de quelques milliers, l'UI history devient lente à charger
- Les vieilles entrées (>1 an) ne sont pas pertinentes pour un rollback
- Compromis : on perd le rollback des très anciennes installs, mais on garde l'UI fluide

### Pourquoi pas de tests E2E navigateur ?

- Selenium / Playwright = beaucoup de complexité pour un projet d'1 utilisateur
- Les tests unitaires + smoke Flask donnent déjà 85% de confiance
- Le reste est testé manuellement en VM (ce que l'utilisateur fait)


## Pour aller plus loin

- [docs/API.md](API.md) - référence des 47 endpoints REST
- [docs/SECURITY.md](SECURITY.md) - détails sur le modèle de sécurité
- [docs/CONTRIBUTING.md](CONTRIBUTING.md) - comment ajouter un profil/thème/route
- [CLAUDE.md](../CLAUDE.md) - guide rapide pour AI assistants
