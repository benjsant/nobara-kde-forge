# Changelog

Tous les changements notables sont documentés ici.

Format : [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning : [SemVer](https://semver.org/lang/fr/) - `MAJOR.MINOR.PATCH`.

---

## [Unreleased]

### Documentation
- Création du pack docs complet : `docs/USER_GUIDE.md`, `ARCHITECTURE.md`, `API.md`, `SECURITY.md`, `TROUBLESHOOTING.md`, `CONTRIBUTING.md`, `CHANGELOG.md`
- README mis à jour pour refléter toutes les features post-port

---

## [0.2.0] - 2026-05-27

Pass de features majeur après le port initial depuis minty_forge.

### Ajouté

#### Profils
- **Profil `communication`** : Signal Desktop, Element (Matrix), LocalSend, Discord (tous Flatpak)
- Curated additions dans tous les profils existants :
  - `base` : `htop`, `btop`, `bat`, `eza`, `tree`
  - `dev` : `gh`, `lazygit`, `zoxide`, `ripgrep`, `fd-find`, `fzf`, `jq`, `tealdeer`, `httpie`, `tmux`, `python3-pip`, `nodejs`, `npm`
  - `multimedia` : `krita`, `kdenlive`, `audacity`, `HandBrake-gui`, `inkscape`, `mkvtoolnix-gui`, `vlc`
  - `office` : `libreoffice`, `xournalpp` + Flatpak Joplin
  - `privacy` : `keepassxc`, `bleachbit`, `kgpg`
  - `gaming` : `solaar`, Flatpak `gpu-screen-recorder`
  - `system` : `partitionmanager`

#### Thèmes
- **Catalogue Kvantum** ([configs/themes_kvantum.json](../configs/themes_kvantum.json)) - KvDark (system), Catppuccin-Mocha-Lavender, Layan
- Nouveau thème GTK : `Sweet-Dark` (EliverLara), `Layan-Dark` (vinceliuice), `Catppuccin-Mocha-Standard-Lavender-Dark` (Fausto-Korpsvart)
- Nouveau curseur : `phinger-cursors-dark` (phisch)
- Onglet "Kvantum" dans le catalogue UI ([routes/themes.py](../routes/themes.py))

#### Backup config KDE
- Nouveau module [utils/kde_backup.py](../utils/kde_backup.py) - backup/restore tar.gz de 15 fichiers config KDE (kdeglobals, kwinrc, plasmarc, panel layout, raccourcis, Kvantum, etc.)
- Stockage : `~/.local/share/nobaraforgekde/backups/`
- Étiquettes optionnelles, validation regex stricte du filename
- Rétention auto à 30 backups max (auto-prune)
- Routes : `/api/kde/backups/{create,restore,delete,list}`
- Section UI "Sauvegardes config bureau"

#### Tweaks rapides
- Nouveau module [utils/plasma_tweaks.py](../utils/plasma_tweaks.py) - reset plasmashell + clear caches
- Nouveau module [utils/services_manager.py](../utils/services_manager.py) - toggle whitelist 5 services systemd (`fstrim.timer`, `bluetooth`, `cups`, `sshd`, `firewalld`)
- Nouveau module [utils/audio_tweaks.py](../utils/audio_tweaks.py) - PipeWire sample rate (44.1/48/96/192 kHz) + codecs BT premium (LDAC/aptX-HD/AAC)
- Nouveau blueprint [routes/tweaks.py](../routes/tweaks.py) - 7 routes
- Section UI "Tweaks rapides" en 3 sous-blocs

#### Panneau Identité système Nobara
- Nouveau module [utils/system_info.py](../utils/system_info.py) - détection kernel patches (CachyOS/BORE/NTSYNC/PREEMPT_DYN via `/boot/config-<kernel>`), LSM, SELinux, sysctls gaming, btrfs, zram
- Route `/api/system/info` (cache 30s)
- Section UI avec pills violet/gris

#### Indicateur services en erreur
- `systemctl --failed` count dans la status-bar (vert si 0, rouge sinon)

#### Frontend
- **Migration Alpine.js (15 KB)** pour la status-bar et le panneau identité Nobara
- Composant `forge()` avec 15 getters computed
- Event `status:updated` dispatché pour compat code legacy
- **Palette violet Nobara** (#9b59b6 primary, #7d3c98 secondary) remplaçant le bleu KDE générique

#### Launcher
- `uv` installé via **DNF en priorité** sur Nobara/Fedora 41+ (`sudo dnf install -y uv`), fallback curl puis pip

### Changé

#### Profil AMD
- **`mesa-vulkan-drivers` → `mesa-vulkan-drivers-freeworld`** (et idem `mesa-va-drivers`, `mesa-vdpau-drivers`). Les variantes `-freeworld` de RPM Fusion incluent les codecs propriétaires (h264/h265/AV1/MPEG-2). Le paquet `mesa-vdpau-drivers` standard n'existe plus dans les dépôts Nobara 43.

#### State manager
- Cap à **500 entries** sur `data/state.json` (drop oldest). Évite la croissance illimitée.

#### Logs
- Rotation : `RotatingFileHandler(maxBytes=5MB, backupCount=3)` → 20 MB max sur disque

#### Configs audio
- Écriture atomique (`tmp + replace`) pour les drop-ins PipeWire/WirePlumber

### Fixé

#### Bugs Nobara compatibility (paquets supprimés/renommés)
- `latte-dock` retiré (n'existe plus sur Fedora 38+)
- `com.mattjakeman.ExtensionManager` retiré du `flatpak.json` (outil GNOME, inutile sur KDE)
- `mscore-fonts-all` retiré (n'existe pas sur Fedora - héritage Mint)
- `numlockx` retiré du profil `base` (outil X11, ineffective sur Wayland qui est défaut)
- `joystickwake` retiré du profil `handheld` (sur PyPI seulement, pas dans les dépôts RPM)

#### DNF5 compatibility
- `dnf config-manager --add-repo` (syntaxe DNF4) remplacé par `curl -sSLo` pour Docker CE et Brave Browser

#### Launcher
- `acpi` retiré de l'auto-install (jamais utilisé - `utils/power.py` lit directement sysfs)

#### State manager (post-audit)
- `print()` calls remplacés par `logging.getLogger("nobaraforgekde.state")` (apparaissent dans le stream SSE + le log fichier)

### Sécurité

- **Backup KDE - defense en profondeur** : whitelist + validation tar (anti path-traversal `..`, anti chemin absolu, regex filename strict)
- **Services systemd** : whitelist côté module ET route
- **Audio** : drop-ins **user-level** uniquement (jamais dans `/etc/`)

### Tests

- 5 nouveaux fichiers de tests : `test_kde_backup.py` (12 tests), `test_plasma_tweaks.py` (6), `test_services_manager.py` (11), `test_audio_tweaks.py` (11), `test_system_info.py` (11)
- Total : **~85 tests** (de 39 avant)

### Doc

- [CLAUDE.md](../CLAUDE.md) mis à jour avec nouveaux modules, features et profil communication

---

## [0.1.0] - 2026-04-XX

Premier port complet depuis [minty_forge](https://github.com/benjsant/minty_forge) (Linux Mint Cinnamon → Nobara KDE).

### Ajouté

- Port complet de minty_forge vers Nobara KDE :
  - `apt` → `dnf`
  - `gsettings` (Cinnamon) → `kwriteconfig6` (KDE Plasma 6)
  - `lightdm + slick-greeter` → `plasma-login-manager`
  - `ufw` → `firewalld`
  - Inhibition veille via `qdbus` PowerManagement
- 15 profils d'installation : base, office, gaming, htpc, handheld, dev, multimedia, docker, distrobox, browsers, privacy, vpn, system, amd, nvidia
- Catalogues thèmes : GTK, Icons, Cursors
- Settings KDE Plasma : ~25 paramètres (thèmes, fonts, night light, screen lock, KWin)
- Intégration outils Nobara natifs : `nobara-welcome`, `nobara-driver-manager`, `nobara-codec-wizard`, `nobara-resolve-wizard`, etc.
- Mode CLI : `--list-profiles`, `--profile`, `--dry-run`
- Snapshot Timeshift optionnel pré-install (mode BTRFS sur Nobara)
- State manager + rollback (`data/state.json`)
- Pre-flight check (conflicts détection + GPU warnings)

### Sécurité

- **Lock file global** ([utils/lockfile.py](../utils/lockfile.py)) - PID file dans `$XDG_RUNTIME_DIR/nobaraforgekde.lock`, signal handlers SIGTERM/SIGINT pour nettoyage propre
- **Anti-CSRF / DNS-rebinding** ([utils/security.py](../utils/security.py)) - middleware Host check + Origin/Referer sur POST/PUT/DELETE
- **Sandbox bwrap** ([utils/sandbox.py](../utils/sandbox.py)) - commandes user-level des thèmes dans un user namespace, FS read-only sauf whitelist
- **Audit log + détection patterns** - `looks_dangerous()` scanne 11 patterns suspects (eval, /dev/tcp, curl|bash, fork bomb, rm -rf /, etc.)
- **Avertissement batterie** sur laptop ([utils/power.py](../utils/power.py))

### Infrastructure

- Validation **Pydantic v2 stricte** (`extra='forbid'`) sur tous les configs JSON
- CI GitHub Actions : matrix Python 3.10-3.13, compile + ruff + pytest
- Pre-commit hooks (ruff, JSON validation, etc.)
- Packaging : `.desktop` file + installer/uninstaller pour le menu KDE

### Tests initiaux

- ~39 tests pytest (schemas round-trip, security middleware, sandbox, lockfile, power, app smoke)

---

## [archive/laptop]

Branche dédiée non mergée dans main. Contient la **gestion PC portable étendue** retirée de main pour rester focused sur l'utilitaire d'installation :

- TLP intégration (battery / power profiles)
- Monitoring laptop (température, ventilation, charge)
- Mode dock / hybrid GPU
- `asusctl` deep integration

Voir https://github.com/benjsant/nobara-kde-forge/tree/archive/laptop pour le code source.

Le seul élément de "gestion laptop" gardé dans main est le **warning batterie** ([utils/power.py](../utils/power.py)) - banner UI quand l'utilisateur lance une install en étant sur batterie (risque de coupure mid-install).

---

## Conventions de versioning pour le futur

- **MAJOR** (X.0.0) : changement incompatible (suppression d'endpoint, changement de schema JSON incompatible, refactor majeur)
- **MINOR** (0.X.0) : nouvelle feature compatible (nouveau profil, nouveau panneau UI, nouvelle route)
- **PATCH** (0.0.X) : bug fix, doc, polish, sécurité non-breaking

Une release crée un tag git annoté + ajoute une section dans ce CHANGELOG.

---

[Unreleased]: https://github.com/benjsant/nobara-kde-forge/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/benjsant/nobara-kde-forge/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/benjsant/nobara-kde-forge/releases/tag/v0.1.0
