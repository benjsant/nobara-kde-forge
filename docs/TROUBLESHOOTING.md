# Troubleshooting

Solutions aux problèmes courants. Si ton problème n'est pas listé, regarde [docs/USER_GUIDE.md](USER_GUIDE.md) ou ouvre une issue.

---

## Sommaire

1. [Lancement / démarrage](#lancement--démarrage)
2. [Sudo / permissions](#sudo--permissions)
3. [Installation de paquets](#installation-de-paquets)
4. [Thèmes](#thèmes)
5. [Paramètres KDE](#paramètres-kde)
6. [Backup / restore KDE](#backup--restore-kde)
7. [Tweaks rapides](#tweaks-rapides)
8. [Plasma Login Manager](#plasma-login-manager)
9. [Audio (PipeWire)](#audio-pipewire)
10. [Performances / UI](#performances--ui)

---

## Lancement / démarrage

### `./nobaraforgeKDE.sh` : "Une autre instance de NobaraForgeKDE tourne deja (PID xxx)"

L'app détecte un lock file existant.

**Cas 1** : tu as vraiment une autre instance ouverte → ferme-la (CTRL+C ou bouton Quitter).

**Cas 2** : l'instance précédente a crashé sans nettoyer.
```bash
# Vérifier si le PID est vivant
ps -p <PID>
# Si pas vivant, supprime le lock manuellement
rm "$XDG_RUNTIME_DIR/nobaraforgekde.lock"
# (fallback si XDG_RUNTIME_DIR vide)
rm /tmp/nobaraforgekde.lock
```

Au prochain `./nobaraforgeKDE.sh`, le lock stale sera détecté et écrasé automatiquement.

---

### Le navigateur ne s'ouvre pas

Le launcher fait `webbrowser.open(URL)` après 2s. Sur certains setups (X11 forwardé, conteneur, etc.), Python n'arrive pas à trouver le navigateur.

**Solution** : ouvre manuellement http://localhost:5000 dans ton navigateur.

---

### `uv: command not found` après installation

Le script a essayé DNF → curl → pip dans cet ordre. Si tous échouent, c'est un problème de PATH.

```bash
# Verifie si uv est installé quelque part
which uv
find / -name "uv" -type f 2>/dev/null

# Probablement dans :
ls -la ~/.local/bin/uv
ls -la ~/.cargo/bin/uv

# Ajoute au PATH
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

# Puis relance
./nobaraforgeKDE.sh
```

**Solution préférée** sur Nobara : `sudo dnf install -y uv` directement.

---

### Erreur Python "Module not found: flask" ou "pydantic"

Le `uv sync` n'a pas tourné ou a échoué.

```bash
# Manuel
cd /chemin/vers/nobara-kde-forge
uv sync
# Test
uv run python -c "import flask, pydantic; print('OK')"
```

Si `uv sync` échoue : vérifie ton fichier `pyproject.toml`, ou supprime `.venv/` et `uv.lock` puis relance.

---

### Port 5000 déjà utilisé

```
[Errno 98] Address already in use
```

Un autre process écoute sur 5000.

```bash
ss -tlnp | grep :5000
# Tue le process si tu sais ce que c'est
# ou change le port dans web_app.py:
# PORT = 5001
```

> Note : changer le port casse aussi le check `register_security(app, port=PORT)` côté middleware Host check. Adapte les deux.

---

## Sudo / permissions

### "Sudo" passe rouge dans la status-bar après quelques minutes

Le cache sudo a expiré. Le launcher bash maintient le cache via un loop background, mais s'il a été tué (suspend OS, etc.), le cache expire.

**Solution rapide** :
```bash
# Dans un terminal
sudo -v
```

Puis re-clique sur l'action dans l'UI. Le cache reste actif ~15 min après chaque `sudo -v`.

**Solution durable** : ferme l'app (Quitter) et relance `./nobaraforgeKDE.sh` (réinitialise le cache + le loop keeper).

---

### Toggle service échoue avec "Cache sudo expire — relancez l'app"

Idem ci-dessus. Le toggle a tenté `sudo -n systemctl enable/disable --now <service>` et sudo a refusé sans password.

---

### `/etc/sudoers.d/nobaraforgekde` reste après crash

Le launcher devrait le nettoyer via `trap cleanup EXIT`, mais si tué par SIGKILL, le trap ne s'exécute pas.

```bash
./nobaraforgeKDE.sh --uninstall
# OU manuellement :
sudo rm -f /etc/sudoers.d/nobaraforgekde
```

---

### `firewall-cmd` demande quand même un password

Le sudoers temporaire n'a pas été créé (échec sudo initial) ou a été supprimé.

```bash
# Vérifie
sudo cat /etc/sudoers.d/nobaraforgekde
# Devrait afficher :
# # Genere par NobaraForgeKDE — supprime a la fermeture
# user ALL=(ALL) NOPASSWD: /usr/bin/firewall-cmd

# Si vide, recreate via relance du launcher
./nobaraforgeKDE.sh
```

---

## Installation de paquets

### "Tache en cours" alors que rien ne tourne

Le `task_lock` est resté coincé après un crash interne.

**Solution** : redémarre l'app (Quitter + `./nobaraforgeKDE.sh`).

---

### DNF lock error : "Another DNF instance running"

Une autre instance DNF tourne quelque part (Discover, dnfdragora, autre terminal, nobara-updater en background).

```bash
# Identifier
ps aux | grep -E "dnf|packagekit"

# Si packagekit en arriere-plan
sudo systemctl stop packagekit
# Relancer l'install via l'UI
```

---

### Paquet "no match for argument: X" lors d'une install

Le paquet n'existe pas (ou plus) dans les dépôts Nobara/Fedora 43.

Cas connus déjà fixés :
- `latte-dock` (retiré F38+) → supprimé du projet
- `mscore-fonts-all` (Mint-only) → supprimé
- `mesa-vdpau-drivers` (retiré F43, → `mesa-vdpau-drivers-freeworld`) → fixé

Si tu rencontres un autre cas :
```bash
# Vérifier la disponibilité
dnf list --available <package>

# Chercher des alternatives
dnf search <package>
```

Puis ouvre une issue avec le nom du paquet pour qu'on le retire / remplace dans le profil.

---

### Flatpak install timeout sur une grosse app (Bottles, Heroic)

Augmente le timeout via variable d'environnement avant de lancer le launcher :

```bash
export NOBARAFORGEKDE_SCRIPT_TIMEOUT=14400  # 4 heures
./nobaraforgeKDE.sh
```

Défaut : 7200 secondes (2h).

---

### Profil installé mais des paquets ont échoué silencieusement

L'install continue même si certains paquets échouent (par design — éviter qu'un paquet introuvable bloque tout le profil).

**Vérification** :
- Logs SSE dans l'UI affichent les `[ERROR]` au passage
- `logs/nobaraforgekde.log` garde la trace persistante
- `Historique` dans l'UI : les entries avec `success=false` (badge rouge)

---

## Thèmes

### Install d'un thème GTK échoue avec "sassc manquant"

Le launcher installe normalement `sassc` au démarrage. Si raté :

```bash
sudo dnf install -y sassc
```

Puis relance l'install du thème.

---

### Thème cloné depuis git mais "Installation terminée mais theme non trouve"

Le script du thème (souvent `./install.sh`) n'a pas placé le thème là où on l'attend.

**Causes courantes** :
- Le script attend une variante spécifique (ex: `./install.sh -t default -c dark`)
- Le `name_to_use` dans le JSON ne matche pas le nom réel généré (ex: thème installé sous `Sweet-Dark-COMPACT` mais on cherche `Sweet-Dark`)

**Solution manuelle** :
```bash
# Voir ce qui a été installé
ls ~/.themes/ ~/.icons/ ~/.local/share/icons/

# Si le nom réel diffère, edite configs/themes_gtk.json (ou autre catalogue)
# et corrige le champ "name_to_use" pour qu'il matche.
```

---

### Thème installé en `~/.themes` mais Plasma ne le voit pas

KDE Plasma scan `~/.themes` pour GTK, mais pour les **thèmes Plasma natifs** (.plasmoid, color-schemes), il scan `~/.local/share/plasma/desktoptheme/`.

Pour appliquer un thème GTK dans KDE → **Paramètres bureau → Thème GTK** dans NobaraForgeKDE (utilise `kwriteconfig6` qui écrit dans `kdeglobals`).

---

### Thème installé en `~/.themes` invisible sur l'écran de connexion

C'est attendu : le DM (plasma-login-manager) tourne en tant qu'utilisateur système, il ne lit pas `~/.themes`.

**Solution** : réinstalle le thème avec la case "Installation système" cochée → install dans `/usr/share/themes`.

---

### `bwrap: Can't create user namespace`

Ton kernel ne permet pas les user namespaces unprivileged (rare sur Nobara, mais possible).

```bash
# Vérifier
cat /proc/sys/kernel/unprivileged_userns_clone
# Doit être 1
```

Si 0 :
```bash
sudo sysctl -w kernel.unprivileged_userns_clone=1
# Et pour rendre persistant :
echo 'kernel.unprivileged_userns_clone = 1' | sudo tee /etc/sysctl.d/99-userns.conf
```

Sinon le sandbox bwrap est désactivé (fallback transparent), l'install marche mais sans isolation.

---

## Paramètres KDE

### "Appliquer la configuration" ne change rien visuellement

Les changements sont écrits via `kwriteconfig6` mais Plasma ne recharge pas toujours en live :
- **Thème de curseur** : nécessite parfois une déconnexion/reconnexion
- **Police titre fenêtres** : nécessite KWin restart (`kwin --replace &`)
- **Décorations fenêtres** : idem

Force un reload :
```bash
qdbus org.kde.KWin /KWin reconfigure
# OU
kwin_wayland --replace &
```

Ou plus radical : **Tweaks rapides → Réinitialiser Plasma**.

---

### Settings retournent à leur ancienne valeur après une déconnexion

`kwriteconfig6` écrit dans `~/.config/kdeglobals`, mais si Plasma a la valeur en mémoire au moment de la déconnexion, il **écrit son cache** par-dessus tes changements.

**Solution** : applique les paramètres ET déclenche un reload AVANT de te déconnecter :
- Bouton "Appliquer la configuration" (déclenche `_notify_kde_reload`)
- OU `qdbus org.kde.KWin /KWin reconfigure`

---

### Kvantum activé mais les apps Qt n'utilisent pas le thème

Il manque la variable `QT_STYLE_OVERRIDE=kvantum`.

```bash
# Pour la session courante
export QT_STYLE_OVERRIDE=kvantum

# Persistant : ajouter dans ~/.config/environment.d/kvantum.conf
mkdir -p ~/.config/environment.d
echo 'QT_STYLE_OVERRIDE=kvantum' > ~/.config/environment.d/kvantum.conf
# Effet à la prochaine connexion
```

Alternative : utilise `kvantummanager` (GUI), il setse la variable correctement.

---

## Backup / restore KDE

### "Nom de sauvegarde invalide" lors d'une restore

Le filename ne matche pas le regex `^kde-\d{8}-\d{6}(-[A-Za-z0-9_-]{1,32})?\.tar\.gz$`.

Causes :
- Tu as renommé manuellement un backup
- Tu as copié un backup d'une autre source

**Solution** : renomme manuellement le fichier pour matcher le format :
```bash
mv "monvieuxbackup.tar.gz" "kde-20250101-120000-recovered.tar.gz"
```

---

### Backup créé mais "Aucun fichier de config a sauvegarder"

Aucun des 15 fichiers whitelisted n'existait dans `~/.config/` au moment du backup. Très rare — vérifie :
```bash
ls ~/.config/kdeglobals ~/.config/kwinrc
```

Si vide, tu n'as probablement jamais ouvert KDE Plasma sur ce compte (config pas encore générée).

---

### Restore ne change rien — KDE garde l'ancien état

`_notify_kde_reload()` est déclenché après extraction, mais Plasma cache certains paramètres. Forcer le reload :

1. **Tweaks rapides → Réinitialiser Plasma** (relance plasmashell)
2. OU déconnexion/reconnexion (clean)

---

### Mon backup contient juste 2-3 fichiers, je m'attendais à plus

Normal — seuls les fichiers existants au moment du backup sont inclus. Si tu n'utilises pas Kate, `katerc` n'existe pas → pas dans le backup. C'est attendu.

Liste des 15 fichiers couverts : voir [docs/USER_GUIDE.md#sauvegardes-config-bureau](USER_GUIDE.md#sauvegardes-config-bureau).

---

## Tweaks rapides

### "Réinitialiser Plasma" : la barre des tâches ne revient pas

`kstart6` a échoué. Tente manuellement :
```bash
plasmashell &
disown
```

Si toujours rien :
```bash
# Force kill complet + redémarrage propre
killall -9 plasmashell
sleep 1
kstart6 plasmashell
```

Vérifie aussi les logs :
```bash
journalctl --user -u plasma-* --since "5 min ago"
```

---

### Toggle d'un service "non installé"

L'UI grise les services absents — pas de bouton. Pour les installer :

| Service | Paquet |
|---|---|
| `fstrim.timer` | `util-linux` (déjà installé sur Nobara) |
| `bluetooth.service` | `bluez` |
| `cups.service` | `cups` |
| `sshd.service` | `openssh-server` |
| `firewalld.service` | `firewalld` (déjà installé sur Nobara) |

```bash
sudo dnf install <package>
# Puis rafraîchir l'UI
```

---

### Sample rate PipeWire changé mais pas pris en compte

`systemctl --user restart pipewire pipewire-pulse wireplumber` ne suffit parfois pas car les apps ouvertes gardent leur sample rate de session.

**Solution** :
1. Ferme toutes les apps audio (Firefox, Spotify, etc.)
2. Bascule à un autre rate puis reviens (force le refresh)
3. OU déconnexion/reconnexion

Vérification :
```bash
pw-metadata 0 clock.rate
# Doit afficher value:'<rate>'
```

---

### Codecs Bluetooth premium activés mais casque reste en SBC

Cas typique : le casque BT a été pairé AVANT l'activation des codecs.

**Solution** : déconnecte + reconnecte le casque (via le widget Bluetooth de la barre tâches). À la reconnexion, WirePlumber négocie LDAC/aptX-HD si supporté par le casque.

Vérification :
```bash
wpctl status | grep -A5 "Default Sink"
# Cherche A2DP-LDAC ou A2DP-aptX-HD
```

---

## Plasma Login Manager

### "SDDM detecte" alors que tu es sur Nobara KDE 43

Cas étrange — Nobara 43+ devrait avoir migré vers plasma-login-manager. Vérifie :

```bash
systemctl status display-manager.service
systemctl is-active plasmalogin.service
systemctl is-active sddm.service
```

Si SDDM toujours actif, faire la migration manuelle :
```bash
sudo dnf install -y plasma-login-manager
sudo systemctl disable --now sddm
sudo systemctl enable --now plasmalogin
# Redémarrer la machine pour appliquer
```

---

### Thème de l'écran de connexion reste Breeze par défaut malgré "Synchroniser"

Le thème de curseur que tu utilises (`kcminputrc`) est dans `~/.local/share/icons/` ou `~/.icons/`. Le DM ne peut pas y accéder.

**Solution** : réinstalle le curseur avec **"Installation système"** cochée dans le catalogue Thèmes → curseurs.

---

## Audio (PipeWire)

### `pw-metadata: command not found`

`pipewire-utils` pas installé.

```bash
sudo dnf install -y pipewire-utils
```

L'app fonctionne sans (current_rate sera `null` dans `/api/tweaks/audio`).

---

### Pas de son après changement de sample rate à 192000 Hz

Tes hauts-parleurs/DAC ne supportent peut-être pas 192 kHz. Reviens à 48000 ou 96000.

```bash
# Verifier ce que ton hardware supporte
pactl list cards | grep -A20 "Available sample rates"
```

---

## Performances / UI

### L'UI rame, le polling de status met du temps

Cause probable : un subprocess en cours qui sature le CPU/IO (gros DNF transaction, gros tar de backup, etc.).

Le polling est toutes les 5s côté frontend + cache 8s côté serveur. Si la machine est saturée, le ressenti est lent.

**Solution** : attends la fin de la tâche en cours (visible dans la task bar).

---

### Le panneau "Identité système Nobara" affiche "Mesa ?" ou "Plasma ?"

Les commandes `plasmashell --version` ou `rpm -q mesa-dri-drivers` ont échoué.

Cas connus :
- `plasmashell` pas dans PATH → tu n'es pas en session KDE
- `mesa-dri-drivers` désinstallé/renommé → on tente fallback mais peut échouer

C'est cosmétique, pas un blocage. Vérifie manuellement :
```bash
plasmashell --version
rpm -q mesa-dri-drivers
```

---

### Status-bar affiche "Services en erreur : 1" — où voir lequel ?

```bash
systemctl --failed
# Detail d'un service
systemctl status <service>.service
journalctl -u <service>.service --since "1 hour ago"
```

Souvent c'est un service Nobara mineur (ex: `accounts-daemon` en cycle d'erreur). L'app marche très bien malgré ça.

---

## Si vraiment rien ne marche

1. **Logs détaillés** : `logs/nobaraforgekde.log` (5 MB max, rotation)
2. **Reset state.json** :
   ```bash
   cp data/state.json data/state.json.bak
   rm data/state.json
   ```
3. **Réinstall complet** :
   ```bash
   ./nobaraforgeKDE.sh --uninstall  # nettoyage fichiers système
   rm -rf .venv uv.lock data/ logs/
   git clean -fdx                    # ⚠ supprime tout untracked
   ./nobaraforgeKDE.sh               # repart from scratch
   ```
4. **Issue GitHub** avec :
   - Version Nobara (`cat /etc/os-release`)
   - Version kernel (`uname -r`)
   - Plasma version (`plasmashell --version`)
   - Commit NobaraForgeKDE (`git rev-parse HEAD`)
   - Reproduction des étapes
   - Logs (`tail -50 logs/nobaraforgekde.log`)
