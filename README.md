# NobaraForgeKDE

![CI](https://github.com/benjsant/nobara-kde-forge/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-green)
![Distribution](https://img.shields.io/badge/Nobara%20KDE-41%2B-orange)
![Plasma](https://img.shields.io/badge/Plasma-6-9b59b6)

Outil d'**automatisation post-installation** pour **Nobara KDE** (Fedora-based, KDE Plasma).
Port du projet [minty_forge](https://github.com/benjsant/minty_forge) (Linux Mint Cinnamon) adapté à l'écosystème Nobara/Fedora/KDE.

Interface web Flask sur `http://localhost:5000` (ou mode CLI). Installe paquets DNF, Flatpaks, paquets externes (VSCode, Docker, Brave…), thèmes GTK/Plasma/icônes/curseurs/Kvantum, configure KDE Plasma, le firewall, le display manager Plasma Login, sauvegarde la config bureau, expose des tweaks rapides (reset Plasma, services systemd, audio PipeWire/BT) et plus.


## Pourquoi ?

Quand on installe une Nobara KDE, on a souvent les mêmes manipulations à faire après l'install : ajouter Steam si pas pris, basculer en mode sombre, installer son IDE préféré, configurer firewalld, mettre des thèmes Plasma cohérents, etc. NobaraForgeKDE rassemble ces actions dans une UI cochable avec rollback, backup config, et tweaks rapides.

C'est un **outil de plus**, pas un remplacement de `nobara-welcome` ou `nobara-updater` - au contraire, il les intègre et les expose dans son UI.


## Lancement

```bash
# Cloner
git clone https://github.com/benjsant/nobara-kde-forge.git
cd nobara-kde-forge

# Tout faire d'un coup (installe uv via DNF si dispo sinon curl, sync deps, sudo, lance Flask)
./nobaraforgeKDE.sh

# Optionnel : installer le raccourci dans le menu KDE
./packaging/install-desktop.sh
```

L'UI s'ouvre dans le navigateur. Sélectionnez vos profils, cochez les paquets/thèmes/options, cliquez "Installer". Voir [docs/USER_GUIDE.md](docs/USER_GUIDE.md) pour le tour complet.

### Mode CLI (sans interface web)

```bash
uv run python nobara_kde_forge.py --list-profiles
uv run python nobara_kde_forge.py --profile gaming,dev
uv run python nobara_kde_forge.py --profile gaming --dry-run
```

### Désinstallation

```bash
./nobaraforgeKDE.sh --uninstall   # Retire les fichiers systeme deposes (sudoers, conf DM)
./packaging/install-desktop.sh --uninstall   # Retire le raccourci KDE
```

> Note : les **paquets installés ne sont PAS supprimés** par `--uninstall`. Pour ça, utilisez le rollback dans l'UI (`Historique → Tout annuler`).


## Profils inclus (16)

| Profil | Contenu principal |
|---|---|
| `base` | Outils essentiels : htop/btop/bat/eza, sassc, kvantum, fastfetch, FiraCode, Flatseal, Warehouse |
| `office` | Thunderbird, LibreOffice, xournalpp, OnlyOffice, Joplin, PDFSlicer |
| `communication` | Signal, Element (Matrix), LocalSend, Discord - tous Flatpaks |
| `gaming` | Steam, gamemode, MangoHud, Heroic, Bottles, ProtonPlus, RetroDECK, solaar, gpu-screen-recorder |
| `htpc` | Steam HTPC, Kodi, gamescope (mode salon) |
| `handheld` | gamescope, goverlay, DeckyLoader (mode Steam Deck-like) |
| `dev` | gcc, cmake, gdb, ripgrep, fd, fzf, jq, gh, lazygit, zoxide, nodejs, npm, python3-pip |
| `multimedia` | mpv, krita, kdenlive, audacity, HandBrake, inkscape, OBS, GIMP, vlc, mkvtoolnix |
| `docker` | virt-manager, qemu, libvirt + Docker CE (repo officiel) |
| `distrobox` | podman, distrobox, BoxBuddy |
| `browsers` | Chromium + Brave (repo officiel) |
| `privacy` | firewall-config, ClamAV, WireGuard, KeePassXC, BleachBit, kgpg |
| `vpn` | 7 backends VPN avec intégration KDE Plasma |
| `system` | gparted, partitionmanager, timeshift, kdeconnect, scrcpy, hplip-gui |
| `amd` | Pilotes Mesa **freeworld** (Vulkan/VDPAU/VA), radeontop, corectrl |
| `nvidia` | Pilotes NVIDIA via `nobara-driver-manager` |

Auto-détection GPU : le profil opposé (NVIDIA si AMD détecté, et vice versa) est **verrouillé** sauf confirmation explicite.


## Features

### Installation
- **Profils d'installation** combinables, avec dédoublonnage paquet/Flatpak en session
- **Mode personnalisé** : choisir paquet par paquet via le bouton "Detail" sur chaque profil
- **Pre-flight check** : détecte conflits (paquet à installer dans X et à supprimer dans Y), warnings GPU
- **Dry-run** : aperçu de ce qui serait installé sans rien faire
- **Snapshot Timeshift** optionnel avant chaque install (si timeshift installé)
- **Rollback** automatique : chaque action enregistrée dans `data/state.json`, annulable depuis l'UI

### Configuration bureau
- **Paramètres KDE** via `kwriteconfig6` : thèmes GTK/Plasma/icônes/curseur/Kvantum, fonts, polices, espaces de travail, veilleuse, VRR, DRM Leasing (gaming Wayland)
- **Catalogue de thèmes** installables depuis git : Orchis, Sweet, Layan, Catppuccin (GTK + Kvantum), Tela, Bibata, Phinger, etc.
- **Mode sombre/clair** persistant dans l'UI
- **Plasma Login Manager** (DM par défaut Nobara/Fedora KDE 42+) : synchro thème/curseur/numlock

### Backup & restore config KDE
- Crée des `tar.gz` horodatés de la config KDE (~15 fichiers : kdeglobals, kwinrc, plasmarc, panel layout, raccourcis, Kvantum, etc.)
- Étiquettes optionnelles, restauration en 2 clics
- Rétention auto à 30 backups max (les plus anciens pruned automatiquement)

### Tweaks rapides
- **Reset Plasma** : kquitapp6 + clear cache + kstart6 (résout les bugs de panel)
- **Vider les caches** : ~/.cache/thumbnails, plasma*, krunner, ksycoca6
- **Services systemd toggleables** : fstrim.timer, bluetooth, cups, sshd, firewalld
- **Audio PipeWire** : sample rate (44.1/48/96/192 kHz) + codecs BT premium (LDAC/aptX-HD/AAC)

### Diagnostic & monitoring
- **Panneau "Identité système Nobara"** : kernel patches détectés (CachyOS/BORE/NTSYNC), LSM, sysctls gaming, btrfs, zram
- **Indicateur services en erreur** dans la status-bar (vert si 0, rouge sinon)
- **Logs SSE temps réel** + historique persistant
- **Avertissement batterie** sur laptop : bannière warning si vous lancez une install sur batterie

### Outils Nobara natifs intégrés
NobaraForgeKDE expose les outils Nobara existants dans son UI plutôt que de les dupliquer :
- `nobara-welcome` - guide d'accueil (Discord, Steam, drivers)
- `nobara-driver-manager` - NVIDIA, asusctl, xpadneo, Broadcom, ROCm
- `nobara-codec-wizard` - codecs multimédia propriétaires
- `nobara-drive-mount-manager` - automount partitions
- `nobara-resolve-wizard` - diagnostic problèmes système
- `nobara-sync` - synchro métadonnées repos
- `nobara-updater` - utilisé par défaut pour les MAJ système (fallback DNF)


## Documentation

| Document | Contenu |
|---|---|
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Manuel utilisateur complet, section par section |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture détaillée pour contributeurs |
| [docs/API.md](docs/API.md) | Référence des 47 endpoints REST |
| [docs/SECURITY.md](docs/SECURITY.md) | Modèle de sécurité (CSRF, sandbox, lockfile, backups) |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | FAQ + résolution des problèmes courants |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Comment contribuer (setup dev, conventions) |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Historique des versions |
| [CLAUDE.md](CLAUDE.md) | Guide technique pour développeurs et IA |


## Configuration

Variable d'environnement | Défaut | Effet
---|---|---
`NOBARAFORGEKDE_SCRIPT_TIMEOUT` | `7200` | Timeout des scripts d'installation (secondes)

Tous les autres réglages se font via l'UI ou en éditant les JSON dans [`configs/`](configs/).


## Architecture (résumé)

```
nobaraforgeKDE.sh          # Launcher bash : uv DNF/curl, sudo, inhibe veille, lance Flask
nobara_kde_forge.py        # Point d'entrée Python (UI ou CLI)
web_app.py                 # Application Flask + blueprints

routes/                    # 9 blueprints, 47 endpoints REST
  ├─ legacy.py             # status, logs SSE, execute, theme, system info
  ├─ profiles.py           # /api/profiles/* - install, dry-run, preflight
  ├─ kde_settings.py       # /api/kde/* - kwriteconfig6 + backups
  ├─ themes.py             # /api/themes/* - catalogues GTK/icons/cursors/kvantum
  ├─ tweaks.py             # /api/tweaks/* - plasma reset, services, audio
  ├─ system.py             # /api/system/* - firewalld
  ├─ login_manager.py      # /api/sddm/* - Plasma Login Manager
  ├─ nobara_tools.py       # /api/nobara/* - lancement outils Nobara natifs
  └─ state_routes.py       # /api/state/* - rollback

utils/                     # 16 modules : subprocess, state, theme_manager, security, sandbox, lockfile, kde_backup, plasma_tweaks, services_manager, audio_tweaks, system_info, power, validation, profile_loader, etc.

schemas/                   # Modèles Pydantic strict (extra='forbid')
configs/                   # JSON : 16 profils, 4 catalogues thèmes, paquets DNF/Flatpak
web/                       # Frontend (HTML + Alpine.js + Vanilla JS + CSS)
tests/                     # 10 fichiers de tests pytest (~85 tests)
```

Détails complets : [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) et [CLAUDE.md](CLAUDE.md).


## Sécurité

- **Lock file global** (PID file dans `$XDG_RUNTIME_DIR`) - interdit deux instances simultanées
- **Middleware anti-CSRF / anti-DNS-rebinding** : `Host` strict + `Origin`/`Referer` requis sur POST
- **Sandbox bwrap** des commandes utilisateur (themes installés depuis git)
- **Whitelist stricte** des services systemd toggleables, des fichiers de config KDE backupés
- **Audit log** systématique des commandes externes avec détection de patterns suspects (`eval`, `/dev/tcp`, `curl|bash`, fork bomb, `rm -rf /`, etc.)
- **Defense en profondeur** sur les backups : regex filename + validation des membres tar (anti path-traversal)

Détails : [docs/SECURITY.md](docs/SECURITY.md).


## Tester

```bash
uv sync --group dev
uv run --group dev pytest tests/ -v
```

CI GitHub Actions : matrix Python 3.10 → 3.13, compile + ruff + pytest.


## Compatibilité

- ✅ **Nobara Linux 41, 42, 43** (KDE Plasma Desktop Edition)
- ✅ **Plasma 6** (utilise `kwriteconfig6`/`kreadconfig6`)
- ⚠️ Fedora KDE 42+ vanilla : devrait fonctionner sauf intégration `nobara-*` (qui retombera en fallback DNF)
- ⚠️ Anciennes Nobara avec SDDM : l'UI affichera un warning et proposera la migration vers `plasma-login-manager`


## Licence

GPL-3.0 - voir [LICENSE](LICENSE).

## Contribuer

Issues et PR bienvenues. Voir [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Les configs de profils dans `configs/profiles/` sont l'endroit le plus facile pour ajouter de la valeur (un nouveau preset = un JSON validé Pydantic).

## Liens

- Repo : https://github.com/benjsant/nobara-kde-forge
- Projet parent : [benjsant/minty_forge](https://github.com/benjsant/minty_forge)
- Nobara Project : https://nobaraproject.org/
