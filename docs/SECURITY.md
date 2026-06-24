# Modèle de sécurité

Détail des protections en place dans NobaraForgeKDE, leur raisonnement, et leurs limites.


## Contexte de menace

NobaraForgeKDE est une application **locale, mono-utilisateur**, qui :
- Écoute sur `127.0.0.1:5000` (pas d'exposition réseau)
- Tourne avec les droits de l'utilisateur (pas root, sauf élévation ponctuelle via sudo)
- Exécute des commandes système (`dnf install`, `systemctl`, scripts d'install de thèmes)
- Lit/écrit dans `~/.config/`, `~/.cache/`, `~/.local/share/`

**Vecteurs de menace pris en compte** :

1. **Autre process local malveillant** qui tenterait des POST vers `127.0.0.1:5000`
2. **DNS rebinding** : page web malveillante qui résout son domaine vers 127.0.0.1
3. **CSRF** : page web externe qui POST cross-origin vers l'API locale
4. **Configs JSON compromises** (suppy chain attack) contenant des commandes malicieuses
5. **Tarballs malicieux** placés dans le dossier backups
6. **Path traversal** dans les noms de backup pour écraser des fichiers hors backup dir
7. **Race conditions** entre deux instances NobaraForgeKDE concurrentes

**Vecteurs NON pris en compte** (hors scope) :
- Attaquant local avec droits root → game over par définition
- Compromission du dépôt git Nobara/Astral/Mesa → pas notre problème
- Compromission de mes commandes via `Bash` tool → l'utilisateur doit toujours review


## Sommaire des protections

| Protection | Module | Couvre |
|---|---|---|
| [Lock file global](#1-lock-file-global) | `utils/lockfile.py` | 2 instances simultanées (race state.json + DNF lock) |
| [Middleware anti-CSRF / DNS rebinding](#2-middleware-anti-csrf--dns-rebinding) | `utils/security.py` | DNS rebinding, CSRF cross-origin |
| [Sandbox bwrap](#3-sandbox-bwrap) | `utils/sandbox.py` | Commandes user-level des thèmes |
| [Audit log + détection patterns](#4-audit-log--détection-patterns-dangereux) | `utils/sandbox.py` | Commandes externes (sudo) où bwrap ne s'applique pas |
| [Backup KDE - whitelist & validation tar](#5-backup-kde--whitelist--validation-tar) | `utils/kde_backup.py` | Path traversal, écrasement de fichiers arbitraires |
| [Whitelist services systemd](#6-whitelist-services-systemd) | `utils/services_manager.py` | Toggle arbitraire de services système |
| [Pas de `shell=True`](#7-pas-de-shelltrue) | `utils/subprocess_utils.py` | Command injection via interpolation |
| [Drop-ins audio user-level](#8-drop-ins-audio-user-level) | `utils/audio_tweaks.py` | Pas d'écriture dans `/etc/` |
| [Sudoers temporaire scopé](#9-sudoers-temporaire-scopé) | `nobaraforgeKDE.sh` | Élévation persistante, scope trop large |
| [Validation Pydantic stricte](#10-validation-pydantic-stricte) | `schemas/` | Configs malformés ou champs inattendus |


## 1. Lock file global

[utils/lockfile.py](../utils/lockfile.py)

### Problème

Si deux instances de NobaraForgeKDE tournent simultanément :
- Conflits sur le `data/state.json` (race au save)
- DNF lock en collision (`/var/lib/dnf/lock`)
- UI 1 ne voit pas les actions de UI 2

### Solution

PID file dans `$XDG_RUNTIME_DIR/nobaraforgekde.lock` (fallback `/tmp/`).

- Au démarrage : si fichier existe et PID vivant → refus avec exit 2
- Si PID stale (process mort) → écrasement
- Au shutdown : `atexit` + handlers **SIGTERM/SIGINT** retirent le lock si PID match

```python
# utils/lockfile.py
def acquire():
    if path.exists():
        existing_pid = read(path)
        if pid_alive(existing_pid) and existing_pid != os.getpid():
            raise LockfileError(existing_pid, path)
    path.write_text(str(os.getpid()))
    atexit.register(_release_if_ours, path, os.getpid())

def install_signal_handlers():
    """atexit ne couvre PAS les signaux. Le bouton 'Quitter' envoie SIGTERM."""
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, _handler)
```

### Limites

- Pas de protection inter-utilisateur (chaque user a son `XDG_RUNTIME_DIR`)
- Race possible entre deux invocations *exactement* simultanées (créneaux < 1ms) → acceptable

### Tests

[tests/test_security.py](../tests/test_security.py) - 5 tests :
- `acquire/release` idempotent même PID
- Bloque si PID étranger vivant
- Écrase si stale
- N'efface pas un lock détenu par autre
- Signal handler retire le lock à SIGTERM (test dans process enfant)


## 2. Middleware anti-CSRF / DNS rebinding

[utils/security.py](../utils/security.py)

### Problème

- Un site web malveillant peut résoudre son domaine vers 127.0.0.1 (DNS rebinding) puis faire des fetch POST cross-origin
- Un onglet sur un autre site peut tenter un POST cross-origin (CSRF)
- Le navigateur enverra alors `Host: evil.com` ou `Origin: https://evil.com`

### Solution

Middleware Flask `before_request` qui :

1. **Host check** (toujours actif) :
   ```python
   if request.headers.get("Host") not in {"localhost", "localhost:5000", "127.0.0.1", "127.0.0.1:5000"}:
       return 421
   ```

2. **Origin/Referer check** sur POST/PUT/DELETE :
   ```python
   if request.method not in SAFE_METHODS:
       value = request.headers.get("Origin") or request.headers.get("Referer")
       if not value or urlparse(value).hostname not in {"localhost", "127.0.0.1"}:
           return 403
   ```

**Enregistré AVANT les blueprints** dans [web_app.py](../web_app.py:32) pour intercepter tout le trafic.

### Limites

- GET sont laissés passer (favoris, refresh navigateur). Une page distante peut lire les GET ? Non - CORS strict empêche le navigateur de lire la réponse cross-origin par défaut.
- curl sans Origin/Referer est refusé sur POST → c'est volontaire (limite l'API aux requêtes navigateur)

### Tests

[tests/test_security.py](../tests/test_security.py) - 7 tests Host + Origin :
- Foreign host rejected (4 cas : evil.com, IPs, etc.)
- Valid host accepted (4 cas : localhost, 127.0.0.1, avec et sans port)
- POST sans Origin/Referer → 403
- POST avec Origin externe → 403
- POST avec Origin localhost → traité par la route (200 ou 400 selon, mais pas 403)
- POST avec Referer seulement → accepté (compat anciens navigateurs)
- GET sans Origin → 200


## 3. Sandbox bwrap

[utils/sandbox.py](../utils/sandbox.py)

### Problème

Les commandes `cmd_user` des thèmes (depuis catalogues git) sont des **strings bash arbitraires** :
```json
"cmd_user": "./install.sh -t lavender -c dark"
```

Si un catalogue est compromis (ou un user clone un thème malveillant), `install.sh` pourrait :
- Écrire dans `~/.ssh/`, `~/.config/Signal/`, etc.
- Exfiltrer via réseau
- Modifier `.bashrc` pour persistance

### Solution

`bubblewrap` (bwrap) enveloppe les commandes user-level :

```python
# utils/sandbox.py
def wrap_user_command(inner_cmd, writable_paths):
    return [
        "bwrap",
        "--ro-bind", "/", "/",      # FS read-only
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--unshare-user-try",       # user namespace
        "--unshare-pid",
        "--unshare-uts",
        "--die-with-parent",
        "--new-session",
        "--share-net",              # network gardé (git clone)
        *[f"--bind={p}={p}" for p in writable_paths],  # dossiers theme
        *inner_cmd,
    ]
```

### Paths writable autorisés

Pour les thèmes user :
- `~/.themes`, `~/.icons`, `~/.local`, `~/.config`, `clone_path` (build dir temp)

Tout le reste du FS est **read-only**. Un `install.sh` qui essaie de toucher `~/.ssh/` échoue.

### Limites

- **Pas applicable aux commandes `sudo`** : l'escalade root casse le user namespace. Pour ces cas, on se rabat sur [§4 audit log](#4-audit-log--détection-patterns-dangereux).
- Fallback transparent si `bwrap` absent (warning loggé, exécution sans sandbox)

### Tests

[tests/test_sandbox.py](../tests/test_sandbox.py) :
- `bwrap_available` détecte la présence du binaire
- `wrap_user_command` retourne la cmd brute si bwrap absent
- Inclut bien `--ro-bind`, `--share-net`, etc.
- Whitelist writable paths injectés correctement


## 4. Audit log + détection patterns dangereux

[utils/sandbox.py:35](../utils/sandbox.py#L35) - `looks_dangerous()`

### Problème

Les commandes externes des profils (`configs/profiles/*.json` → `external.cmd`) font souvent du `sudo` (install Docker, Brave, etc.). Bwrap ne peut pas les contenir.

### Solution

1. **Audit log systématique** : la commande complète est affichée dans les logs avant exécution
   ```
   [AUDIT] Commande : sudo bash -c 'curl ... && dnf install ...'
   ```

2. **Détection de patterns** : 11 regex compilées
   ```python
   _DANGEROUS_PATTERNS = [
       (r"\beval\b",                  "appel a eval"),
       (r"/dev/tcp/",                  "redirection /dev/tcp (reverse shell)"),
       (r"/dev/udp/",                  "redirection /dev/udp"),
       (r"\bnc\s+.*-e\b",              "netcat -e"),
       (r"\bncat\s+.*--exec\b",        "ncat --exec"),
       (r"\bmkfifo\b",                 "FIFO (pipe nomme)"),
       (r"curl\s+.*\|\s*(bash|sh)\b",  "curl pipe shell"),
       (r"wget\s+.*\|\s*(bash|sh)\b",  "wget pipe shell"),
       (r":\(\)\{\s*:\|:&\s*\};:",     "fork bomb"),
       (r"\brm\s+-rf\s+/(\s|$)",       "rm -rf /"),
       (r"\bdd\s+.*of=/dev/",          "dd vers /dev/* (disk wipe)"),
   ]
   ```

3. **Warning sans blocage** : `looks_dangerous` retourne les findings, qui sont **affichés** mais n'empêchent pas l'exécution (l'utilisateur garde le dernier mot).

### Limites

- Détection par regex → contournable trivialement (`e\val`, `c\url|bash`). Le but n'est PAS de bloquer mais de **flagger** des configs suspectes pour review humaine.
- Ne couvre pas tous les patterns dangereux (impossible exhaustivement)

### Tests

[tests/test_sandbox.py](../tests/test_sandbox.py) - 11 patterns testés en positive + negative.


## 5. Backup KDE - whitelist & validation tar

[utils/kde_backup.py](../utils/kde_backup.py)

### Problème

Sans validation :
- Un attaquant pourrait poser un `.tar.gz` malicieux dans `~/.local/share/nobaraforgekde/backups/`
- Au restore, le tar contient des membres avec `../../etc/passwd` → écrasement
- Ou des membres avec chemin absolu `/etc/shadow`
- Ou des liens symboliques pointant hors du dossier

### Solution multicouche

**Couche 1 - Filename strictement validé** :
```python
_FILENAME_RE = re.compile(r'^kde-\d{8}-\d{6}(-[A-Za-z0-9_-]{1,32})?\.tar\.gz$')

def _validate_filename(filename):
    if not _FILENAME_RE.match(filename):
        raise BackupError("Nom de sauvegarde invalide")
    target = BACKUP_DIR / filename
    if not target.exists() or not target.is_file():
        raise BackupError(...)
    # Validation multi-niveau : verifie que ca resolve bien dans BACKUP_DIR
    target.resolve().relative_to(BACKUP_DIR.resolve())  # leve ValueError si symlink escape
```

**Couche 2 - Filtrage des membres tar** :
```python
def _member_is_safe(member):
    name = member.name
    if not name or name.startswith("/"):
        return False  # chemin absolu
    if ".." in Path(name).parts:
        return False  # path traversal
    if name not in CONFIG_FILES:
        return False  # hors whitelist
    return member.isfile()  # pas un symlink, pas un dossier
```

**Couche 3 - Whitelist stricte** (15 fichiers) : seuls les fichiers explicitement listés dans `CONFIG_FILES` sont extraits. Tout autre membre est silencieusement skippé (compté dans `skipped`).

### Limites

- Si l'attaquant a écriture sur `~/.local/share/nobaraforgekde/backups/`, il pourrait écrire un tar valide avec des configs KDE modifiées (mais qui resteraient dans la whitelist). C'est dans le scope user - pas une élévation
- Pas de signature/HMAC sur les backups (overkill pour un outil mono-user)

### Tests

[tests/test_kde_backup.py](../tests/test_kde_backup.py) :
- Path traversal `../../etc/passwd` bloqué
- Chemin absolu `/etc/passwd.tar.gz` bloqué
- Filename random `random.tar.gz` bloqué
- Tar malicieux : membres hors whitelist + `..` extraits dans `skipped`, pas créés
- Retention 30 → vieilles backups pruned auto


## 6. Whitelist services systemd

[utils/services_manager.py](../utils/services_manager.py)

### Problème

Sans whitelist, un POST avec `{"name": "anything.service"}` pourrait stopper/désactiver des services critiques (sshd, NetworkManager, plasmalogin, …).

### Solution

```python
ALLOWED_SERVICES = {
    "fstrim.timer":      "TRIM SSD hebdomadaire",
    "bluetooth.service": "Bluetooth (casques, manettes)",
    "cups.service":      "Impression CUPS",
    "sshd.service":      "Serveur SSH entrant",
    "firewalld.service": "Pare-feu firewalld",
}

def toggle_service(name, enable):
    if name not in ALLOWED_SERVICES:
        return False, f"Service non autorise : {name}"
    ...
```

Vérification **dans le module ET dans la route** (validation multi-niveau).

### Limites

- L'utilisateur peut bien sûr toggle n'importe quel service au terminal - c'est volontaire de limiter l'UI


## 7. Pas de `shell=True`

[utils/subprocess_utils.py](../utils/subprocess_utils.py)

### Problème

`subprocess.run("dnf install " + user_input, shell=True)` est vulnérable à command injection (`user_input = "; rm -rf /"`).

### Solution

`run_command()` accepte uniquement une **liste d'arguments** (pas une string) :
```python
def run_command(cmd, ...):
    # cmd doit etre une liste, JAMAIS une string
    result = subprocess.run(cmd, ...)  # shell=False par défaut
```

Conséquence : aucune interpolation de string n'est interprétée par le shell. `["dnf", "install", "; rm -rf /"]` traite `"; rm -rf /"` comme un nom de paquet (DNF le rejettera).

### Exception : `["bash", "-c", cmd]` pour les commandes externes

Les `external.cmd` des profils sont des strings bash (Docker repo setup, etc.). Pour les exécuter, on fait `["bash", "-c", cmd]`. C'est volontaire et géré par [§4 audit log](#4-audit-log--détection-patterns-dangereux).

### Limites

- Cette protection est UNIQUEMENT pour les inputs runtime. Le contenu des JSON `configs/profiles/*.json` est sous le contrôle du développeur - pas une protection contre supply-chain attack du dépôt.


## 8. Drop-ins audio user-level

[utils/audio_tweaks.py](../utils/audio_tweaks.py)

### Problème

Modifier `/etc/pipewire/` ou `/etc/wireplumber/` nécessite sudo, casse le multi-user, et est globalement plus risqué.

### Solution

Toutes les modifs audio écrivent dans `~/.config/{pipewire,wireplumber}/.conf.d/` :
- Pas de sudo
- Affecte seulement l'utilisateur courant
- Trivial à annuler (supprime le fichier)
- Atomic via tmp + replace

```python
_PIPEWIRE_CONF = Path.home() / ".config/pipewire/pipewire.conf.d/10-nobaraforgekde-rate.conf"

def _atomic_write_text(path, content):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content)
    tmp.replace(path)  # rename atomique POSIX
```

### Limites

- Aucune - c'est le pattern recommandé par PipeWire/WirePlumber upstream.


## 9. Sudoers temporaire scopé

[nobaraforgeKDE.sh:151](../nobaraforgeKDE.sh#L151)

### Problème

`firewall-cmd` est appelé fréquemment (status check à chaque page load). Sans NOPASSWD, prompt password à chaque clic → UX cassée.

### Solution

Le launcher bash dépose un sudoers **scopé** à `firewall-cmd` uniquement :

```bash
# /etc/sudoers.d/nobaraforgekde
$USER ALL=(ALL) NOPASSWD: /usr/bin/firewall-cmd
```

Auto-cleanup au `EXIT` via `trap cleanup` :
```bash
trap cleanup EXIT
cleanup() {
    sudo -n rm -f /etc/sudoers.d/nobaraforgekde
}
```

### Limites

- Si l'app crash avec SIGKILL → trap pas exécuté → sudoers reste. Mitigation : `./nobaraforgeKDE.sh --uninstall` nettoie manuellement.
- Un local user qui a déjà sudo pourrait utiliser le NOPASSWD pour autre chose ? Non - c'est limité strictement à `/usr/bin/firewall-cmd`, et cet user a déjà sudo de toute façon.


## 10. Validation Pydantic stricte

[schemas/](../schemas/)

### Problème

Une typo dans un JSON profil (`"frlatpak"` au lieu de `"flatpak"`) passerait silencieusement → champ ignoré → comportement inattendu.

### Solution

Tous les modèles utilisent `extra='forbid'` :

```python
class Profile(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str = Field(..., min_length=1)
    icon: str = ...
    apt: list[ProfileAptPackage] = ...
    ...
```

Conséquence : tout champ inattendu **lève une `ValidationError`**. Visible :
- En CI via `tests/test_schemas.py` (round-trip de tous les configs)
- Au démarrage via `profile_loader.load_all_profiles()`

### Validations spécifiques

- **`icon`** doit être dans `VALID_ICONS` (11 valeurs : `box`, `wrench`, `gamepad`, etc.)
- **`flatpak.app`** doit matcher `^[a-zA-Z0-9._-]+$` et contenir au moins un `.`
- **`name`** non vide (min_length=1)


## Protections de runtime

### Lock task_lock

[routes/shared.py](../routes/shared.py) - un `threading.Lock` empêche deux installs de tourner en parallèle :

```python
with task_lock:
    if current_task["running"]:
        return jsonify({"success": False, "error": "Tache en cours"}), 409
    current_task.update(running=True, name=...)
```

Empêche deux clics rapides sur "Installer" de spawner deux subprocess concurrents.

### Atomic file writes

`state.json`, `pipewire/wireplumber.conf` - tous via `tmp + replace`. Si crash mid-write, le fichier précédent reste intact.

### Cap des fichiers à croissance illimitée

- `data/state.json` : cap à **500 entries** (drop oldest)
- `logs/nobaraforgekde.log` : rotation **5 MB × 4** = 20 MB max
- `~/.local/share/nobaraforgekde/backups/` : retention **30 backups** max

Voir [docs/USER_GUIDE.md](USER_GUIDE.md) et le commit "Add bounded retention to prevent unbounded growth" pour détails.


## Reporting de vulnérabilités

Si tu identifies une vulnérabilité :

1. **NE PAS** ouvrir une issue GitHub publique
2. Envoyer un mail à l'adresse du repo owner (`git log --format='%ae' main | head -1`)
3. Inclure : description, vecteur d'attaque, impact estimé, version (`git rev-parse HEAD`)
4. Une réponse sous 7 jours est l'objectif (meilleur effort, c'est un projet bénévole)

Les fix se font sur main puis sont signalés dans [CHANGELOG.md](CHANGELOG.md) avec un préfixe `[SECURITY]`.
