# Manuel utilisateur

Guide complet de l'interface NobaraForgeKDE, section par section.


## Sommaire

1. [Premier lancement](#premier-lancement)
2. [Vue d'ensemble de l'interface](#vue-densemble-de-linterface)
3. [Status bar](#status-bar)
4. [Panneau Identité système Nobara](#panneau-identité-système-nobara)
5. [Profils d'installation](#profils-dinstallation)
6. [Outils Nobara natifs](#outils-nobara-natifs)
7. [Paquets optionnels](#paquets-optionnels)
8. [Catalogue de thèmes](#catalogue-de-thèmes)
9. [Paramètres du bureau (KDE)](#paramètres-du-bureau-kde)
10. [Sauvegardes config bureau](#sauvegardes-config-bureau)
11. [Tweaks rapides](#tweaks-rapides)
12. [Écran de connexion (Plasma Login)](#écran-de-connexion-plasma-login)
13. [Historique & rollback](#historique--rollback)
14. [Pare-feu (firewalld)](#pare-feu-firewalld)
15. [Logs temps réel](#logs-temps-réel)
16. [Mode CLI](#mode-cli)
17. [Variables d'environnement](#variables-denvironnement)


## Premier lancement

```bash
./nobaraforgeKDE.sh
```

Au premier lancement, le launcher :

1. **Vérifie Python 3.10+** (devrait toujours être OK sur Nobara/Fedora 41+)
2. **Installe `uv` si absent** - priorité à `dnf install -y uv` (Nobara/Fedora ≥41), sinon script officiel astral.sh, sinon `pip --user uv`
3. **`uv sync`** - synchronise les dépendances (Flask, Pydantic) dans un venv local `.venv/`
4. **Demande sudo** - passwd cache maintenu en background pour la durée de la session
5. **Installe les outils requis** : `sassc`, `git` si absents
6. **Crée un sudoers temporaire** `/etc/sudoers.d/nobaraforgekde` pour `firewall-cmd` sans mot de passe (nettoyé à la fermeture)
7. **Inhibe la mise en veille** via `qdbus` PowerManagement (évite que le système s'endorme pendant une install)
8. **Lance Flask** sur `http://localhost:5000` et ouvre le navigateur

L'app ouvre l'UI dans le navigateur par défaut. Si rien ne s'ouvre, va manuellement sur http://localhost:5000.

> **Arrêt propre** : `CTRL+C` dans le terminal ou bouton "Quitter" dans l'UI. Le sudoers temp et l'inhibit veille sont nettoyés via le `trap cleanup EXIT` du launcher.


## Vue d'ensemble de l'interface

L'UI est une page unique (scroll vertical) organisée en sections :

```
┌─────────────────────────────────────────────────────────┐
│  Header (titre + toggle thème + bouton Quitter)         │
├─────────────────────────────────────────────────────────┤
│  Status bar (9 indicateurs : internet/sudo/python/...)   │
├─────────────────────────────────────────────────────────┤
│  Panneau Identité système Nobara (pills violet/gris)    │
├─────────────────────────────────────────────────────────┤
│  Warnings (outils manquants, batterie) [optionnels]     │
├─────────────────────────────────────────────────────────┤
│  Task bar (visible uniquement pendant une tâche)        │
├─────────────────────────────────────────────────────────┤
│  Profils d'installation (grille de cartes)              │
├─────────────────────────────────────────────────────────┤
│  Outils Nobara natifs                                   │
├─────────────────────────────────────────────────────────┤
│  Paquets optionnels                                     │
├─────────────────────────────────────────────────────────┤
│  Catalogue thèmes (4 onglets : GTK/Icons/Cursors/Kvantum)│
├─────────────────────────────────────────────────────────┤
│  Paramètres du bureau (KDE settings)                    │
├─────────────────────────────────────────────────────────┤
│  Sauvegardes config bureau                              │
├─────────────────────────────────────────────────────────┤
│  Tweaks rapides (3 sous-blocs : plasma/services/audio)  │
├─────────────────────────────────────────────────────────┤
│  Écran de connexion (Plasma Login)                      │
├─────────────────────────────────────────────────────────┤
│  Historique & rollback                                  │
├─────────────────────────────────────────────────────────┤
│  Pare-feu firewalld                                     │
├─────────────────────────────────────────────────────────┤
│  Logs temps réel (SSE)                                  │
└─────────────────────────────────────────────────────────┘
```


## Status bar

Une rangée de 9 indicateurs sous le header, mis à jour toutes les 5 secondes :

| Indicateur | Signification | Vert / Rouge |
|---|---|---|
| **Internet** | Connectivité (ping fedoraproject.org:80) | Connecté / Pas d'internet |
| **Sudo** | Cache sudo actif (`sudo -n true`) | Cache OK / Cache expiré |
| **Python** | Python 3.10+ détecté | OK / version trop ancienne |
| **DNF** | Nombre de paquets dans `configs/install.json` | - |
| **Optionnel** | Nombre de paquets dans `configs/optional_install.json` | - |
| **Flatpaks** | Nombre de Flatpaks dans `configs/flatpak.json` | - |
| **Themes** | Nombre total de thèmes dans les catalogues | - |
| **Disque libre** | Espace libre sur `/` en Go | Vert si > 5 Go |
| **Alimentation** | Batterie/secteur (laptop uniquement) | Secteur / Batterie |
| **Services en erreur** | `systemctl --failed` count | Vert si 0, rouge sinon |

Si **Sudo** passe rouge en cours de session : le cache a expiré. Relance l'app ou tape `sudo -v` dans un terminal.
Si **Services en erreur** passe à un nombre rouge : ouvre un terminal et `systemctl --failed` pour diagnostiquer.


## Panneau Identité système Nobara

Deux rangées de "pills" affichent ce que Nobara fait déjà pour toi :

**Ligne 1 - Identité de base :**
- `Nobara 43` - version OS
- `Kernel 7.0.9 (CachyOS+BORE+NTSYNC+PREEMPT_DYN) HZ=1000` - kernel avec patches détectés (parsing `/boot/config-<kernel>`)
- `Plasma 6.6.4` - version Plasma
- `Mesa 26.1.0` - version Mesa
- `KDE wayland` - session type

**Ligne 2 - Détails système :**
- `LSM: lockdown+yama+apparmor+bpf+landlock` - Linux Security Modules actifs (extrait de `/sys/kernel/security/lsm`)
- `SELinux: disabled` - état SELinux (Nobara désactive SELinux par défaut)
- `Sysctl gaming: split_lock=0 max_map=ok mtu=on` - sysctls tunés gaming par Nobara
- `btrfs /@ +zstd:1` - filesystem racine (compression activée ?)
- `zram 8.0 Go` - RAM compressée en swap

> **Pourquoi c'est utile** : ça te permet de voir ce que Nobara a déjà configuré pour ne pas faire de doublons (ex: si `Sysctl gaming` est déjà à `ok`, pas besoin de retoucher).

Survol des pills : tooltip avec détails (kernel complet, liste LSM complète, options btrfs, etc.).


## Profils d'installation

La section la plus grosse de l'UI. Chaque profil est une carte cliquable.

### Sélection de profils

Clique sur une carte pour la cocher (✓ apparaît en haut à droite). Plusieurs profils peuvent être sélectionnés en même temps - les paquets en commun sont dédupliqués automatiquement.

### Boutons en haut

| Bouton | Effet |
|---|---|
| **Tout cocher** | Sélectionne tous les profils |
| **Tout décocher** | Vide la sélection |
| **Aperçu** | Dry-run : affiche ce qui serait installé sans rien faire. Indique status de chaque paquet (`to_install`/`installed`/`duplicate`/`absent`) |
| **Pre-flight** | Analyse statique : compte les paquets à installer, détecte les **conflits** (un paquet à installer dans X et à supprimer dans Y) et les **warnings GPU** (ex: AMD profile + NVIDIA hardware) |
| **Exporter** | Télécharge la sélection sous forme de JSON (`nobaraforgekde_profiles.json`) - utile pour partager une config |
| **Importer** | Charge un JSON exporté précédemment |

### Sélection fine d'un profil

Sur chaque carte, le bouton **Detail** ouvre une modale qui liste tous les paquets du profil (DNF / Flatpak / External / Remove) avec leur statut. Tu peux cocher/décocher individuellement et cliquer "Installer la sélection".

### Snapshot Timeshift

Si timeshift est installé et configuré (`./nobaraforgeKDE.sh` détecte au démarrage), une checkbox apparaît sous les profils : **"Snapshot timeshift avant l'installation (recommandé pour rollback rapide)"**. Coche-la avant de lancer l'install - Timeshift en mode BTRFS prend ~5-10 secondes et permet un rollback complet du système.

### Lancement de l'installation

Le bouton **"Installer les profils sélectionnés"** est le déclencheur principal. Workflow :

1. Si snapshot coché → `timeshift --create --tags D`
2. `dnf check-update` (sans `upgrade`)
3. Pour chaque profil sélectionné dans l'ordre `PROFILE_ORDER` :
   - Installer les paquets DNF (avec dédoublonnage `seen_apt`)
   - Installer les Flatpaks (avec dédoublonnage `seen_flatpak`)
   - Exécuter les commandes externes (avec audit log + `looks_dangerous()` check)
   - Supprimer les paquets listés dans `remove`
4. Mise à jour de l'historique (`data/state.json`) avec rollback_cmd pour chaque action

Le bouton se grise pendant l'install. Tu peux **annuler** via le bouton "Annuler" qui apparaît dans la task bar (envoie SIGKILL au subprocess en cours).

### Détection GPU automatique

Au démarrage, `lspci` est parsé pour détecter le GPU. Conséquences :

- **Profil suggéré** : Le profil correspondant à ton GPU a un badge "Suggéré" doré
- **Profil verrouillé** : Le profil opposé (NVIDIA si tu es AMD et vice versa) est grisé. Tu peux le débloquer manuellement en cliquant dessus (cas multi-GPU ou eGPU)


## Outils Nobara natifs

Une grille de 7 boutons pour lancer les outils Nobara existants sans passer par un terminal :

- **Nobara Welcome** - premier lancement, presets HTPC/handheld
- **Driver Manager** - NVIDIA, asusctl, xpadneo, Broadcom, ROCm
- **Drive Mount Manager** - automount partitions (fstab GUI)
- **Codec Wizard** - codecs propriétaires (h264, h265…)
- **Resolve Wizard** - diagnostic + auto-fix problèmes système
- **Nobara Sync** - synchro métadonnées repos
- **Nobara Updater** - mise à jour système

Si un outil n'est pas installé, le bouton est grisé avec un tooltip indiquant comment l'installer (`sudo dnf install nobara-*`).

Ces outils s'ouvrent dans **ta session graphique** (process détaché du serveur Flask), pas dans le navigateur.


## Paquets optionnels

Liste de paquets pratiques mais non essentiels : `hplip`, `sane-backends`, `cabextract`, `p7zip-plugins`, `unrar`, etc.

Chaque paquet affiche son statut (`installé` / `non installé`). Le bouton **"Installer tous les paquets optionnels"** installe ceux qui ne le sont pas encore.

Édite [configs/optional_install.json](../configs/optional_install.json) pour ajouter/retirer des paquets.


## Catalogue de thèmes

4 onglets, chacun avec son catalogue git-installable :

| Onglet | Catalogue | Exemples |
|---|---|---|
| **GTK** | `configs/themes_gtk.json` | Breeze, Orchis-Dark, Sweet-Dark, Layan-Dark, Catppuccin-Mocha |
| **Icones** | `configs/themes_icons.json` | breeze, Tela-dark |
| **Curseurs** | `configs/themes_cursors.json` | breeze_cursors, Bibata-Modern-Classic, phinger-cursors-dark |
| **Kvantum** | `configs/themes_kvantum.json` | KvDark (système), Catppuccin-Mocha-Lavender, Layan |

### Filtres

- **"Masquer les déjà installés"** : cache les thèmes dont une copie est détectée dans `~/.themes`, `~/.icons`, `~/.local/share/icons`, `~/.local/share/plasma/desktoptheme`, `~/.config/Kvantum`, ou les équivalents `/usr/share/`
- **"Installation système"** (case cochée par défaut) : install dans `/usr/share/themes` (sudo). Décoche pour install user-only dans `~/.themes` etc.

### Installation d'un thème

Clique "Installer → /usr/share" sur une carte. Workflow :

1. `git clone --depth 1 <url> /tmp/<theme>` dans un répertoire temporaire
2. **Sandbox bwrap** activé pour les commandes user-level (filesystem read-only sauf `~/.themes`, `~/.icons`, `~/.local`, `~/.config`, clone path)
3. Audit log : `looks_dangerous(cmd)` détecte patterns suspects (`eval`, `curl|bash`, `rm -rf /`, etc.) et émet des warnings
4. Exécution de `cmd_user` ou `cmd_root` (depuis le JSON) dans le clone
5. Vérification post-install : le thème est-il maintenant détecté ?

Si tout OK → message succès + le thème apparaît dans la liste **Paramètres du bureau** pour application.

### Important pour les thèmes Plasma Login Manager

Pour qu'un thème soit utilisable sur l'écran de connexion, il **doit être installé en `/usr/share/`** (pas dans `~/.themes`) car le DM tourne en tant qu'utilisateur système. Coche "Installation système" pour ces thèmes.


## Paramètres du bureau (KDE)

~25 paramètres KDE Plasma exposés via `kwriteconfig6`/`kreadconfig6`. Organisés en grille de groupes.

### Apparence
- **Thème GTK** - appliqué dans `kdeglobals` / `[General]` / `Name`
- **Thème d'icônes** - `kdeglobals` / `[Icons]` / `Theme`
- **Thème de curseur** + taille (24/32/36/48/64) - `kcminputrc` / `[Mouse]`
- **Thème Plasma** - `plasmarc` / `[Theme]` / `name`
- **Schéma de couleurs** - `kdeglobals` / `[General]` / `ColorScheme` (BreezeDark, BreezeLight, OrchisDark…)
- **Thème Kvantum** - `~/.config/Kvantum/kvantum.kvconfig` / `[General]` / `theme`

### Polices
- **Police générale** - `kdeglobals` / `[General]` / `font`
- **Police fixe (terminal/code)** - `kdeglobals` / `[General]` / `fixed`
- **Police titre fenêtres** - `kdeglobals` / `[WM]` / `activeFont`

### Bureau / Fenêtres
- **Nombre de bureaux virtuels** (1-20) - `kwinrc` / `[Desktops]` / `Number`
- **Décoration fenêtres** - `kwinrc` / `[org.kde.kdecoration2]` / `theme`
- **Boutons à gauche** / **à droite** - `[org.kde.kdecoration2]` / `ButtonsOnLeft`, `ButtonsOnRight`
- **Animation de minimisation** - `kwinrc` / `[Plugins]` / `minimizeanimationEnabled`
- **Simple clic** (vs double-clic) - `kdeglobals` / `[KDE]` / `SingleClick`

### Veilleuse (Night Color)
- **Activer** - `kwinrc` / `[NightColor]` / `Active`
- **Température** (1700-6500K) - `[NightColor]` / `NightTemperature`
- **Mode** - `[NightColor]` / `Mode`

### Écran de verrouillage
- **Timeout** (minutes) - `kscreenlockerrc` / `[Daemon]` / `Timeout`
- **Auto-lock** - `[Daemon]` / `Autolock`

### Gaming (Plasma 6+ Wayland)
- **VRR Policy** (0=Never, 1=Auto, 2=Always) - `kwinrc` / `[Wayland]` / `VrrPolicy`
- **DRM Leasing** (pour VR Wayland) - `kwinrc` / `[Wayland]` / `WaylandDRMLease`

### Aperçu des modifications

Avant d'appliquer, l'**aperçu** affiche les changements en JSON (côté droit du panneau). Tu vois exactement ce qui sera modifié.

### Application

Bouton **"Appliquer la configuration"** :
1. Validation des valeurs (range checks sur night_light_temp, cursor_size, num_desktops, vrr_policy)
2. Pour chaque paramètre modifié : `kwriteconfig6 --file X --group Y --key Z value`
3. `dbus-send` à `KGlobalSettings.notifyChange` pour recharger Plasma en live (pas besoin de se déconnecter)

Bouton **"Exporter config KDE actuelle"** : ouvre `/api/kde/export` qui télécharge un dump JSON de la config courante (pour bug reports, partage entre machines).

### Mode sombre rapide

Le bouton "Mode sombre/clair" du header bascule entre `BreezeDark` et `BreezeLight` via `plasma-apply-colorscheme` (fallback `kwriteconfig6` si absent).


## Sauvegardes config bureau

Backup/restore de la config KDE en `.tar.gz` horodaté.

### Couverture

15 fichiers de config (whitelist stricte) :
- `kdeglobals`, `kwinrc`, `plasmarc`, `kcminputrc`, `kscreenlockerrc`
- `kglobalshortcutsrc`, `khotkeysrc` (raccourcis clavier custom)
- `plasma-org.kde.plasma.desktop-appletsrc` (**layout des panels et widgets**)
- `plasmashellrc`, `dolphinrc`, `konsolerc`, `katerc`, `krunnerrc`, `kxkbrc`
- `Kvantum/kvantum.kvconfig`

Tout est stocké dans `~/.local/share/nobaraforgekde/backups/` au format `kde-YYYYMMDD-HHMMSS[-label].tar.gz`.

### Créer un backup

1. Saisis une étiquette optionnelle (max 32 chars alphanum + `-_`) dans le champ texte, ex: `avant-experiences`
2. Clique **"Créer une sauvegarde"**
3. Toast vert avec le nombre de fichiers sauvegardés
4. Le backup apparaît dans la liste

### Restaurer un backup

1. Clique **"Restaurer"** sur la ligne du backup voulu
2. Confirmation requise (la config actuelle sera **écrasée**)
3. Extraction dans `~/.config/` (filtrée contre la whitelist + checks anti `..` et chemins absolus)
4. `_notify_kde_reload()` déclenché → la plupart des changements sont visibles en live

> **Astuce** : avant d'expérimenter avec un thème ou des paramètres, fais un backup étiqueté `avant-X`. Si ça ne te plaît pas, restore en 2 clics.

### Rétention automatique

Au-delà de **30 backups**, les plus anciens sont automatiquement supprimés. Ça évite que le dossier grossisse à l'infini.

### Sécurité

Chaque membre du tar est validé contre la whitelist + vérifié pour `..` et chemin absolu, même si le tar a été créé par nous (validation multi-niveau contre un éventuel tar malicieusement échangé hors de l'app).


## Tweaks rapides

Trois sous-blocs pour les opérations qu'on fait sinon en terminal.

### Réparation rapide

| Bouton | Effet | Cas d'usage |
|---|---|---|
| **Réinitialiser Plasma** | `kquitapp6 plasmashell` (fallback `killall`) → `rm -rf ~/.cache/plasma*` → `kstart6 plasmashell` (détaché) | Barre des tâches buggée, widgets gelés, notifications cassées |
| **Vider les caches** | Nettoie `~/.cache/thumbnails`, `plasma*`, `krunner`, `icon-cache.kcache`, `ksycoca6` | Miniatures cassées, KRunner lent, manque d'espace disque |

Le toast vert indique l'espace récupéré en Mo.

### Services systemd

Une grille de toggles pour 5 services courants :

| Service | Recommandé | Quand activer |
|---|---|---|
| **fstrim.timer** | ✓ ON | TRIM hebdo SSD (longévité) |
| **bluetooth.service** | si BT utilisé | Casques, manettes BT |
| **cups.service** | si imprimante | Impression CUPS |
| **sshd.service** | par défaut OFF | Accès SSH entrant distant |
| **firewalld.service** | ✓ ON | Pare-feu système |

Le toggle déclenche `sudo -n systemctl enable/disable --now <service>`. Si le cache sudo a expiré, un message clair t'invite à relancer l'app ou `sudo -v`.

> Services non installés sur le système : affichés en gris avec mention "non installé" (pas de toggle).

### Audio (PipeWire)

Deux contrôles :

**Sample rate** : actuel + sélecteur (44100 / 48000 / 96000 / 192000 Hz). Apply écrit dans `~/.config/pipewire/pipewire.conf.d/10-nobaraforgekde-rate.conf` (drop-in user-level, atomique via tmp+replace) puis `systemctl --user restart pipewire pipewire-pulse wireplumber`.

**Codecs Bluetooth premium** : toggle ON/OFF. Active `LDAC + aptX-HD + AAC` dans `~/.config/wireplumber/wireplumber.conf.d/51-nobaraforgekde-bt-codecs.conf`. Nécessaire pour les casques BT haut de gamme qui sinon tombent en SBC (qualité dégradée).


## Écran de connexion (Plasma Login)

Affiche l'état du DM (Display Manager) actuel et permet de synchroniser sa config avec celle de ton bureau.

### Détection

- Si `plasmalogin.service` actif → "Plasma Login Manager (Nobara/Fedora KDE 42+ default)"
- Si `sddm.service` actif → warning UI proposant la migration manuelle :
  ```bash
  sudo dnf install plasma-login-manager
  sudo systemctl disable --now sddm
  sudo systemctl enable --now plasmalogin
  ```
- Si aucun → message d'erreur

### Synchroniser

Le bouton **"Synchroniser avec le bureau actuel"** copie ces valeurs depuis ta config KDE vers `/etc/plasmalogin.conf.d/nobaraforgekde.conf` :

- `Theme/CursorTheme` = ton thème de curseur actuel (lu depuis `kcminputrc`)
- `Theme/CursorSize` = la taille
- `General/Numlock` = `on`

> **Important** : les thèmes utilisés sur l'écran de connexion doivent être dans `/usr/share/themes` ou `/usr/share/icons` (pas `~/.themes` !) car le DM tourne en utilisateur système.


## Historique & rollback

Toutes les actions destructives (install/remove via DNF, Flatpak install, commande externe) sont **enregistrées dans `data/state.json`** avec une `rollback_cmd` inverse.

### Vue d'ensemble

La section affiche les N dernières actions (cap à 500 entrées max - les plus anciennes sont droppées).

Chaque ligne montre :
- Type d'action (`dnf_install`, `dnf_remove`, `flatpak_install`, `external_install`)
- Cible (nom du paquet/app)
- Status (succès/échec)
- Timestamp
- Profil source (si applicable)

### Boutons

| Bouton | Effet |
|---|---|
| **Rafraîchir** | Recharge depuis `data/state.json` |
| **Annuler dernière** | Exécute la `rollback_cmd` de la dernière action et retire l'entrée |
| **Tout annuler** | Itère sur toutes les actions (en ordre inverse), exécute leurs rollback. Saute les actions sans rollback dispo |
| **Effacer historique** | Vide `state.json` (sans rollback) - utile après cleanup manuel |

### Limitations du rollback

- **Commandes externes** (`external_install` - VSCode, Docker repo, etc.) n'ont **pas de rollback automatique** (metadata `manual_rollback: True`). Tu vois l'historique mais le rollback est à faire à la main.
- **Configurations KDE** ne passent pas par le state_manager (utilise `kwriteconfig6` direct). Pour ces changements, utilise plutôt **Sauvegardes config bureau** (backup avant + restore).


## Pare-feu (firewalld)

Affiche le statut de `firewalld` + zone par défaut + sortie de `firewall-cmd --list-all`.

| Bouton | Effet |
|---|---|
| **Activer** | `sudo systemctl enable --now firewalld` |
| **Désactiver** | `sudo systemctl disable --now firewalld` |
| **Rafraîchir** | Refresh du statut |

Si la status-bar montre "Sudo" rouge, ces boutons échoueront. Tape `sudo -v` au terminal avant.

> Le launcher bash a déjà configuré `/etc/sudoers.d/nobaraforgekde` pour permettre `sudo -n firewall-cmd` (sans mot de passe), spécifiquement pour les opérations firewall fréquentes. Ce sudoers est **supprimé à la fermeture** de l'app.


## Logs temps réel

Le panneau du bas affiche les logs en streaming SSE (Server-Sent Events). Tout ce qui passe par le logger `nobaraforgekde` apparaît ici en temps réel + dans `logs/nobaraforgekde.log`.

### Toolbar

- **Indicateur de connexion** (point vert/rouge) : statut SSE
- **Effacer** : vide le panneau (ne touche pas au fichier disque)
- **Auto-scroll: ON/OFF** : suit automatiquement les nouvelles lignes

### Niveaux de log

- `[OK]` / `[INFO]` - succès, étapes normales
- `[WARN]` - situations inhabituelles non bloquantes
- `[ERROR]` - échecs
- `[AUDIT]` - commande externe sur le point d'être exécutée (avec sa ligne complète + détection de patterns suspects)

### Rotation

Le fichier `logs/nobaraforgekde.log` est en rotation : **5 Mo par fichier, 3 sauvegardes** = 20 Mo max sur disque. Au-delà, les plus anciens sont supprimés automatiquement.


## Mode CLI

Pour scripting ou utilisation sans navigateur :

```bash
# Lister les profils disponibles
uv run python nobara_kde_forge.py --list-profiles

# Installer un ou plusieurs profils
uv run python nobara_kde_forge.py --profile gaming
uv run python nobara_kde_forge.py --profile gaming,dev,multimedia

# Dry-run (preview sans installer)
uv run python nobara_kde_forge.py --profile gaming --dry-run

# Help
uv run python nobara_kde_forge.py --help
```

Le mode CLI réutilise la même logique d'installation que l'UI (via `scripts.profile_install.install_profile`), avec sortie console colorée (utils/logging_utils).


## Variables d'environnement

| Variable | Défaut | Effet |
|---|---|---|
| `NOBARAFORGEKDE_SCRIPT_TIMEOUT` | `7200` | Timeout (secondes) des scripts d'install lancés via `/api/execute/*`. Augmente si tu installes des gros packs sur connexion lente. |
| `XDG_RUNTIME_DIR` | `/run/user/<uid>` | Emplacement du lock file (fallback `/tmp` si absent) |
| `XDG_CONFIG_HOME` | `~/.config` | Lu par `kwriteconfig6` pour résoudre les paths des fichiers de config KDE |


## Astuces

### Premier setup recommandé sur Nobara fraîche

1. **Sauvegarde config bureau** avant de toucher à quoi que ce soit (étiquette `installation-fraiche`)
2. **Profil `base`** + ton profil principal (`dev`, `gaming`, etc.)
3. **Themes** : applique un set cohérent (Sweet GTK + Sweet KDE + Tela icons + Bibata cursors par exemple)
4. **Paramètres bureau** : règle Night Color, screen lock timeout, font size
5. **Tweaks rapides** : active `fstrim.timer`, configure le sample rate audio si besoin
6. Nouveau backup étiqueté `apres-setup-initial`

### Si l'UI fige

Le bouton **Quitter** envoie SIGTERM proprement. Si vraiment bloqué : `pkill -f "python.*nobara_kde_forge"` au terminal. Le lock file `$XDG_RUNTIME_DIR/nobaraforgekde.lock` est nettoyé par le handler SIGTERM ou détecté comme "stale" au prochain démarrage.

### Voir les vrais paquets DNF qui seraient installés

Mode CLI avec dry-run :
```bash
uv run python nobara_kde_forge.py --profile gaming --dry-run | grep INSTALL
```

### Partager une sélection de profils

UI → **Exporter** → tu obtiens `nobaraforgekde_profiles.json`. Envoie-le. Sur l'autre machine : **Importer** → la sélection est restaurée.

---

Voir aussi : [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) pour les problèmes courants.
