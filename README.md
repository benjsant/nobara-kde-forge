# NobaraForgeKDE

![CI](https://github.com/benjsant/nobara-kde-forge/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-GPL--3.0-green)
![Distribution](https://img.shields.io/badge/Nobara%20KDE-41%2B-orange)

Outil d'**automatisation post-installation** pour **Nobara KDE** (Fedora-based, KDE Plasma).
Port du projet [minty_forge](https://github.com/benjsant/minty_forge) (Linux Mint Cinnamon) adapté à l'écosystème Nobara/Fedora/KDE.

Interface web Flask sur `http://localhost:5000` (ou mode CLI). Installe paquets DNF, Flatpaks, paquets externes (VSCode, Docker, Brave, etc.), thèmes GTK/Plasma/icônes/curseurs, configure KDE Plasma, le firewall, le display manager Plasma Login et plus.

---

## Pourquoi ?

Quand on installe une Nobara KDE, on a souvent les mêmes manipulations à faire après l'install : ajouter Steam si pas pris, basculer en mode sombre, installer son IDE préféré, configurer firewalld, mettre des thèmes Plasma cohérents, etc. NobaraForgeKDE rassemble ces actions dans une UI cochable + rollback.

C'est un **outil de plus**, pas un remplacement de `nobara-welcome` ou `nobara-updater` — au contraire, il les intègre et les expose dans son UI.

---

## Lancement

```bash
# Cloner
git clone https://github.com/benjsant/nobara-kde-forge.git
cd nobara-kde-forge

# Tout faire d'un coup (installe uv si absent, sync deps, demande sudo, lance Flask)
./nobaraforgeKDE.sh

# Optionnel : installer le raccourci dans le menu KDE
./packaging/install-desktop.sh
```

L'UI s'ouvre dans le navigateur. Sélectionnez vos profils, cochez les paquets/thèmes/options, cliquez "Installer".

### Mode CLI (sans interface web)

```bash
uv run python nobara_kde_forge.py --list-profiles
uv run python nobara_kde_forge.py --profile gaming,dev
uv run python nobara_kde_forge.py --profile gaming --dry-run
```

### Désinstallation

```bash
./nobaraforgeKDE.sh --uninstall   # Retire les fichiers systeme deposes (sudoers, conf DM, TLP)
./packaging/install-desktop.sh --uninstall   # Retire le raccourci KDE
```

> Note : les **paquets installés ne sont PAS supprimés** par `--uninstall`. Pour ça, utilisez le rollback dans l'UI (`Historique → Tout annuler`).

---

## Profils inclus

| Profil | Contenu |
|---|---|
| `base` | Outils essentiels : sassc, kvantum, fastfetch, FiraCode, Flatseal, Warehouse |
| `office` | Thunderbird, OnlyOffice, PDFSlicer |
| `gaming` | Steam, gamemode, MangoHud, Heroic, Bottles, ProtonPlus, RetroDECK |
| `htpc` | Steam HTPC, Kodi, gamescope (mode salon) |
| `handheld` | gamescope, joystickwake, DeckyLoader (mode Steam Deck-like) |
| `dev` | gcc, g++, make, cmake, gdb, strace, ltrace |
| `multimedia` | mpv, celluloid, yt-dlp, Elisa, OBS, GIMP |
| `docker` | virt-manager, qemu, libvirt + Docker CE (repo officiel) |
| `distrobox` | podman, distrobox, BoxBuddy |
| `browsers` | Chromium + Brave (repo officiel) |
| `privacy` | firewall-config, ClamAV, WireGuard |
| `vpn` | 7 backends VPN avec intégration KDE Plasma |
| `system` | gparted, timeshift, kdeconnect, scrcpy, hplip-gui |
| `amd` | Pilotes AMD Mesa Vulkan, radeontop, corectrl |
| `nvidia` | Pilotes NVIDIA via `nobara-driver-manager` |

Auto-détection GPU : le profil opposé (NVIDIA si AMD détecté, et vice versa) est **verrouillé** sauf confirmation explicite.

---

## Outils Nobara natifs intégrés

NobaraForgeKDE expose les outils Nobara existants dans son UI plutôt que de les dupliquer :

- `nobara-welcome` — guide d'accueil (Discord, Steam, drivers)
- `nobara-driver-manager` — NVIDIA, asusctl, xpadneo, Broadcom, ROCm
- `nobara-codec-wizard` — codecs multimédia propriétaires
- `nobara-drive-mount-manager` — automount partitions
- `nobara-resolve-wizard` — diagnostic problèmes système
- `nobara-sync` — synchro métadonnées repos
- `nobara-updater` — utilisé par défaut pour les MAJ système (fallback DNF)

---

## Features

- **Profils d'installation** combinables, avec dédoublonnage paquet/Flatpak
- **Rollback** automatique : chaque action enregistrée dans `data/state.json`, annulable depuis l'UI
- **Pre-flight check** : détecte conflits (paquet à installer dans X et à supprimer dans Y), warnings GPU
- **Snapshot Timeshift** optionnel avant chaque install (si timeshift installé)
- **Paramètres bureau KDE** via `kwriteconfig6` : thèmes GTK/Plasma/icônes/curseur/Kvantum, fonts, polices, espaces de travail, veilleuse, VRR, DRM Leasing (gaming Wayland)
- **Catalogue de thèmes** installables depuis git (Orchis, Tela, Bibata-Modern…)
- **Plasma Login Manager** (DM par défaut Nobara/Fedora KDE 42+) : synchro thème/curseur/numlock
- **Firewall** : statut + activation/désactivation firewalld
- **Logs SSE temps réel** + historique persistant
- **Mode sombre/clair** persistant dans l'UI

---

## Capture d'écran

> _À venir — n'hésitez pas à contribuer une capture via PR._

---

## Configuration

Variable d'environnement | Défaut | Effet
---|---|---
`NOBARAFORGEKDE_SCRIPT_TIMEOUT` | `7200` | Timeout des scripts d'installation (secondes)

Tous les autres réglages se font via l'UI ou en éditant les JSON dans [`configs/`](configs/).

---

## Architecture sommaire

```
nobara_kde_forge.py          # Point d'entree Python (UI ou CLI)
nobaraforgeKDE.sh            # Launcher bash : uv sync, sudo, inhibe veille, lance Flask
web_app.py                   # Application Flask + blueprints
routes/                      # Endpoints API : profiles, kde, login_manager, nobara_tools, etc.
scripts/                     # Logique d'installation (DNF, Flatpak, profils, thèmes)
utils/                       # subprocess, state, theme_manager, validation, security, sandbox, lockfile
schemas/                     # Modèles Pydantic strict
configs/                     # JSON : profils, paquets, thèmes
web/                         # Frontend (HTML + Vanilla JS + CSS)
tests/                       # pytest (39 tests)
```

Détails complets dans [CLAUDE.md](CLAUDE.md).

---

## Tester

```bash
uv sync --group dev
uv run --group dev pytest tests/ -v
```

Tests :
- Round-trip Pydantic sur tous les configs JSON (15 profils + 7 configs autonomes)
- Smoke Flask : boot, ping des 8 endpoints clés
- Couverture des endpoints critiques (profiles, nobara, login_manager)

CI GitHub Actions : matrix Python 3.10 → 3.13 (~10s par job).

---

## Compatibilité

- ✅ **Nobara Linux 41, 42, 43** (KDE Plasma Desktop Edition)
- ⚠️ Fedora KDE 42+ vanilla : devrait fonctionner sauf intégration `nobara-*` (qui retombera en fallback DNF)
- ⚠️ Anciennes Nobara avec SDDM : l'UI affichera un warning et proposera la migration vers `plasma-login-manager`

---

## Licence

GPL-3.0 — voir [LICENSE](LICENSE).

## Contribuer

Issues et PR bienvenues. Les configs de profils dans `configs/profiles/` sont l'endroit le plus facile pour ajouter de la valeur (un nouveau preset = un JSON validé Pydantic).

## Liens

- Repo : https://github.com/benjsant/nobara-kde-forge
- Projet parent : [benjsant/minty_forge](https://github.com/benjsant/minty_forge)
- Nobara Project : https://nobaraproject.org/
