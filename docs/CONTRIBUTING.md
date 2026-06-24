# Contributing

Merci de l'intérêt ! Ce guide couvre le setup dev, les conventions et les patterns courants pour ajouter de la valeur au projet.

---

## Sommaire

1. [Setup dev](#setup-dev)
2. [Conventions](#conventions)
3. [Pre-commit hooks](#pre-commit-hooks)
4. [Ajouter un profil](#ajouter-un-profil)
5. [Ajouter un thème au catalogue](#ajouter-un-thème-au-catalogue)
6. [Ajouter une route REST](#ajouter-une-route-rest)
7. [Ajouter un test](#ajouter-un-test)
8. [Workflow git](#workflow-git)
9. [Convention de commit](#convention-de-commit)

---

## Setup dev

```bash
# Cloner
git clone https://github.com/benjsant/nobara-kde-forge.git
cd nobara-kde-forge

# Setup uv (sur Nobara 41+)
sudo dnf install -y uv

# Synchroniser deps (incl. group dev)
uv sync --group dev

# Verifier l'environnement
uv run python -c "import flask, pydantic; print('OK')"

# Lancer l'app en mode dev
./nobaraforgeKDE.sh
```

### Outils requis

- **Python 3.10+** (cible Nobara 41+ qui ship Python 3.13)
- **uv** (Astral) — gestion des deps
- **git** — versioning
- **sassc**, **bwrap** — pour les tests de thèmes / sandbox

### Outils recommandés

- **ruff** (installé via `uv sync --group dev`) — lint + autofix
- **pre-commit** — hooks de validation
- **pytest** — tests

---

## Conventions

### Python

- **Style** : ruff strict (`select = ["E", "F", "I", "B", "SIM", "UP", "C4"]`, voir [pyproject.toml](../pyproject.toml))
- **Line length** : 110 (relax de la PEP 8)
- **f-strings** plutôt que `.format()` ou `%`
- **Type hints** sur les signatures publiques (best-effort sur le reste)
- **Docstrings** en français, courtes, en haut des modules et des fonctions publiques
- **JAMAIS `shell=True`** dans subprocess. Utilise `utils.subprocess_utils.run_command([list])`.

### Naming

- Modules : `snake_case.py`
- Classes : `PascalCase`
- Fonctions / variables : `snake_case`
- Constantes globales : `UPPER_SNAKE`
- Variables privées de module : préfixe `_` (ex: `_lock_path()`, `_cache`)

### Routes Flask

- Préfixe `/api/` pour toutes
- Blueprints dans `routes/`, un fichier par domaine fonctionnel
- Toujours `request.get_json(silent=True) or {}` (pas de 500 sur JSON malformé)
- Toujours retourner `{"success": bool, "error": "..." si false, ...}` au minimum
- Codes HTTP : 200/400/403/404/409/421/500 (voir [docs/API.md](API.md))

### Frontend

- HTML + CSS + Vanilla JS + Alpine.js
- Pas de build step, pas de transpilation
- Functions JS définies à la racine du `<script>` dans `app.js`
- Pour les sections nouvelles, **préférer Alpine** (composant + `x-data`) plutôt que vanilla `innerHTML`

---

## Pre-commit hooks

```bash
uv tool install pre-commit
pre-commit install
```

Hooks actifs ([.pre-commit-config.yaml](../.pre-commit-config.yaml)) :
- `trailing-whitespace`, `end-of-file-fixer`
- `check-yaml`, `check-json` (valide les configs JSON !)
- `check-merge-conflict`
- `check-executables-have-shebangs`
- `mixed-line-ending`
- `ruff` (lint + autofix)

`ruff-format` est désactivé par défaut (génère beaucoup de diff cosmétique). Active-le manuellement si tu veux :
```bash
uv run --group dev ruff format .
```

---

## Ajouter un profil

**Le plus facile pour contribuer** — un nouveau profil = un JSON.

### 1. Créer le fichier

```bash
cp configs/profiles/base.json configs/profiles/monprofil.json
```

Édite le JSON :
```json
{
  "name": "Mon Profil",
  "description": "Description courte qui apparait dans la carte UI",
  "icon": "box",
  "apt": [
    { "name": "package1", "description": "Description courte" },
    { "name": "package2", "description": "Description courte" }
  ],
  "flatpak": [
    { "app": "com.example.App", "description": "Description" }
  ],
  "external": [
    {
      "name": "Mon installer custom",
      "description": "Installation via repo officiel X",
      "cmd": "sudo bash -c 'curl -sSLo /etc/yum.repos.d/X.repo https://X/X.repo && dnf install -y X'"
    }
  ],
  "remove": []
}
```

### 2. Validation des champs

| Champ | Type | Contraintes |
|---|---|---|
| `name` | str | min_length=1 |
| `description` | str | défaut: "" |
| `icon` | str | doit être dans `VALID_ICONS` |
| `apt[].name` | str | min_length=1 (nom paquet DNF/RPM) |
| `flatpak[].app` | str | regex `^[a-zA-Z0-9._-]+$`, doit contenir au moins un `.` |
| `external[].name` | str | min_length=1 |
| `external[].cmd` | str | min_length=1 (commande bash) |
| `remove[].name` | str | min_length=1 |

**`VALID_ICONS`** (voir [schemas/profile.py](../schemas/profile.py)) :
```
box, wrench, gamepad, cpu, gpu, code, film, shield, server, docker, office
```

### 3. Ajouter dans PROFILE_ORDER

[routes/profiles.py:38](../routes/profiles.py#L38) — l'ordre détermine l'affichage dans l'UI :

```python
PROFILE_ORDER = ["base", "office", "communication", "gaming", "htpc", "handheld",
                 "dev", "multimedia", "docker", "distrobox", "amd", "nvidia",
                 "privacy", "vpn", "browsers", "system", "monprofil"]  # <- ajouter ici
```

### 4. Tester

```bash
# Validation Pydantic
uv run pytest tests/test_schemas.py -v

# Mode CLI : dry-run
uv run python nobara_kde_forge.py --profile monprofil --dry-run

# UI
./nobaraforgeKDE.sh
# Le profil apparait dans la grille
```

### 5. Pull request

Commit message : `Add profile: <slug> (<short description>)`

Inclure dans le body : pourquoi ce profil, quel use case, quel hardware/use case ça couvre que les profils existants ne couvrent pas.

---

## Ajouter un thème au catalogue

### 1. Choisir le catalogue

| Catalogue | Type de thème |
|---|---|
| `configs/themes_gtk.json` | GTK 2/3/4, installé via `~/.themes` ou `/usr/share/themes` |
| `configs/themes_icons.json` | Icônes, installé via `~/.icons` ou `~/.local/share/icons` |
| `configs/themes_cursors.json` | Curseurs (subset des icônes) |
| `configs/themes_kvantum.json` | Kvantum, installé via `~/.config/Kvantum` |

### 2. Structure d'une entrée

```json
{
  "name": "MonTheme",
  "name_to_use": "MonTheme-Dark",
  "url": "https://github.com/author/mon-theme.git",
  "cmd_user": "./install.sh -c dark",
  "cmd_root": "sudo ./install.sh -c dark -d /usr/share/themes",
  "description": "Description courte pour la carte UI"
}
```

| Champ | Effet |
|---|---|
| `name` | Affiché dans la liste UI |
| `name_to_use` | Nom du dossier après install (vérifié par `is_theme_installed`) |
| `url` | Repo git à cloner (`--depth 1`) |
| `cmd_user` | Commande exécutée si "Installation utilisateur" cochée |
| `cmd_root` | Commande exécutée si "Installation système" cochée (sudo) |
| `description` | Affiché dans la carte UI |

**Convention** : `cmd_user` ne doit JAMAIS faire `sudo` (cassera le sandbox bwrap). `cmd_root` doit commencer par `sudo`.

### 3. Tester

```bash
# UI : recharger le catalogue
./nobaraforgeKDE.sh
# Navigate -> Themes a installer -> onglet correspondant
# Click "Rafraichir catalogue"
# Click "Installer" sur ton thème
```

Vérifier dans les logs SSE :
- `[AUDIT] Commande : ./install.sh ...` (la commande complète)
- Warnings éventuels si patterns suspects détectés
- `[OK] Theme MonTheme-Dark installe : /path/...`

Puis :
- Aller dans **Paramètres bureau → Thème GTK** (ou Icones/Curseurs/Kvantum)
- Le nouveau thème doit apparaître dans le sélecteur

---

## Ajouter une route REST

### 1. Choisir le blueprint approprié

| Blueprint | Domaine |
|---|---|
| `routes/legacy.py` | Status, logs, execute scripts, theme legacy |
| `routes/profiles.py` | Profils d'installation |
| `routes/kde_settings.py` | KDE settings + backups |
| `routes/themes.py` | Catalogue thèmes |
| `routes/tweaks.py` | Plasma reset, services, audio |
| `routes/system.py` | Firewalld |
| `routes/login_manager.py` | Plasma Login Manager |
| `routes/nobara_tools.py` | Outils Nobara natifs |
| `routes/state_routes.py` | Rollback |

Si aucun ne correspond → crée un nouveau blueprint (voir step 3).

### 2. Ajouter la route

```python
# routes/tweaks.py (exemple)
@bp.route('/api/tweaks/mon-feature', methods=['POST'])
def mon_feature():
    data = request.get_json(silent=True) or {}
    param = data.get("param", "default")

    # Validation
    if not param:
        return jsonify({"success": False, "error": "param requis"}), 400

    try:
        # Logique métier (dans utils/ idéalement)
        from utils.mon_module import faire_le_truc
        result = faire_le_truc(param)

        log_success(f"Feature {param} appliquee")
        return jsonify({"success": True, "result": result})

    except Exception as e:
        log_error(f"Echec feature {param} : {e}")
        return jsonify({"success": False, "error": str(e)}), 500
```

### 3. Si nouveau blueprint nécessaire

Créer `routes/mon_domaine.py` :
```python
from flask import Blueprint, jsonify, request
from routes.shared import log_info, log_error, log_success

bp = Blueprint("mon_domaine", __name__)

@bp.route('/api/mon-domaine/feature')
def feature():
    ...
```

Puis enregistrer dans `web_app.py` :
```python
from routes import (
    ...
    mon_domaine,
)
...
app.register_blueprint(mon_domaine.bp)
```

### 4. Tests

Ajouter dans `tests/test_app_smoke.py` au minimum :
```python
def test_mon_feature_get(client):
    """Smoke test : la route répond."""
    r = client.get('/api/mon-domaine/feature', headers={"Host": "localhost:5000"})
    assert r.status_code in (200, 400)  # selon l'implementation
```

Et un test dédié si la logique est complexe (voir [§ Ajouter un test](#ajouter-un-test)).

### 5. Documenter

Ajouter l'endpoint dans [docs/API.md](API.md). Structure :
- Méthode + path
- Body (si POST/PUT)
- Réponse (exemple JSON)
- Codes d'erreur possibles

### 6. Frontend (si applicable)

Si l'endpoint est appelé depuis l'UI :
- Section HTML dans `web/templates/index.html`
- Fonction JS dans `web/static/js/app.js` (préférer un composant Alpine si nouvelle section)
- Appeler `loadMonFeature()` dans `DOMContentLoaded`

---

## Ajouter un test

### Convention

- 1 fichier de tests par module : `tests/test_<module>.py`
- Fonctions de test : `def test_<feature>():`
- Fixtures : `tmp_path`, `monkeypatch` (pytest built-in)

### Patterns courants

**Test d'un module utils avec accès filesystem** :
```python
import importlib
import pytest

@pytest.fixture
def my_module(tmp_path, monkeypatch):
    """Module avec Path.home() redirige vers tmp_path."""
    import pathlib
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    from utils import mon_module
    importlib.reload(mon_module)
    return mon_module, tmp_path


def test_creation_fichier(my_module):
    mod, fake_home = my_module
    mod.do_something()
    assert (fake_home / "expected.txt").exists()
```

**Test d'une route Flask** :
```python
@pytest.fixture
def client():
    import os
    os.chdir(ROOT)
    from web_app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        c.environ_base["HTTP_HOST"] = "localhost:5000"
        yield c

def test_my_route(client):
    r = client.post('/api/mon-route',
                    json={"param": "value"},
                    headers={"Origin": "http://localhost:5000"})
    assert r.status_code == 200
    assert r.json["success"] is True
```

**Mocking subprocess** :
```python
from types import SimpleNamespace
import subprocess

def test_command_handling(monkeypatch):
    def fake_run(cmd, **kw):
        return SimpleNamespace(stdout="active\n", stderr="", returncode=0)
    monkeypatch.setattr(subprocess, "run", fake_run)

    from utils.services_manager import get_service_status
    status = get_service_status("fstrim.timer")
    assert status["active"] is True
```

### Lancer les tests

```bash
# Tous
uv run --group dev pytest tests/ -v

# Un module
uv run --group dev pytest tests/test_kde_backup.py -v

# Un test précis
uv run --group dev pytest tests/test_kde_backup.py::test_full_cycle -v

# Avec couverture (si pytest-cov installé)
uv run --group dev pytest tests/ --cov=utils --cov=routes
```

---

## Workflow git

### Branches

- **`main`** : branche stable, recevoir les merges via PR (pas de push direct sauf cas urgents)
- **`feature/<slug>`** : feature/refactor en cours, push à volonté
- **`archive/<slug>`** : code historique (ex: `archive/laptop` — gestion PC portable archivée)

### Création d'une feature branch

```bash
git checkout main
git pull
git checkout -b feature/ma-feature
# Implémenter + commits
git push -u origin feature/ma-feature
```

### Avant de merger

```bash
# Tests passent
uv run --group dev pytest tests/

# Lint OK
uv run --group dev ruff check .

# Compile-check
uv run python -m compileall -q routes scripts utils schemas tests

# Bash launcher OK
bash -n nobaraforgeKDE.sh
```

CI fait ça automatiquement sur push/PR.

### Merge vers main

- **Préférer fast-forward** quand l'historique est linéaire (`git merge --ff-only`)
- Squash si la feature a plein de commits "WIP"/"fix typo" (`git rebase -i HEAD~N` avant merge)
- Pas de merge commits pour les petites features (garde l'historique propre)

---

## Convention de commit

### Format

```
<subject>            ← une seule ligne, ~70 chars max

<body explicatif>    ← plusieurs paragraphes possibles

<footers>            ← Co-Authored-By, Fixes #123, etc.
```

### Subject

- Verbe à l'**impératif présent** : `Add`, `Fix`, `Refactor`, `Update`, `Remove`
- Pas de point final
- Préfixe optionnel par domaine : `UI:`, `Doc:`, `Test:`, `CI:`, `Security:`

### Exemples (de l'historique du projet)

```
Add KDE config backup/restore feature

UI: Alpine.js migration (status-bar + identity panel) + Nobara purple theme

Fix Nobara package names + curated package additions across profiles

Security: bwrap sandbox for user-level theme installs + audit log

Doc: update CLAUDE.md with new modules, features, profiles

Launcher: prefer DNF for uv install, drop unused acpi

Polish: atomic audio config writes + structured state logging
```

### Body

- Pourquoi ce changement (le "what" se voit dans le diff)
- Choix techniques notables
- Trade-offs
- Liens vers issue/PR si applicable

### Co-Authored-By

Si Claude a aidé sur le code (comme dans ce projet) :
```
Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Checklist PR

Avant d'ouvrir une PR :

- [ ] Tests passent (`pytest tests/`)
- [ ] Ruff OK (`ruff check .`)
- [ ] Pre-commit hooks ne râlent pas
- [ ] Doc mise à jour si applicable :
  - [ ] [docs/API.md](API.md) si nouvelle route
  - [ ] [docs/USER_GUIDE.md](USER_GUIDE.md) si nouvelle section UI
  - [ ] [docs/ARCHITECTURE.md](ARCHITECTURE.md) si module nouveau / refactor structural
  - [ ] [CHANGELOG.md](CHANGELOG.md) entry dans `## [Unreleased]`
- [ ] Si profil ajouté : `name`, `description`, `icon` valides + entry dans `PROFILE_ORDER`
- [ ] Si route nouvelle : code HTTP cohérent + format de réponse standard
- [ ] Si module utils nouveau : `tests/test_<module>.py` créé

---

## Questions / discussions

- **Issue GitHub** pour bugs et features requests
- **Discussion GitHub** pour les questions design / "comment on fait X"

Le projet est petit, je (mainteneur unique) lis tout. Patience pour les reviews — c'est du bénévolat.
