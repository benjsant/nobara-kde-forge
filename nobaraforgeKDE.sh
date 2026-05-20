#!/bin/bash
# =============================================================
# NobaraForgeKDE - Script tout-en-un
# =============================================================
# 1. Verifie Python 3
# 2. Installe uv si absent, puis synchronise les dependances (uv sync)
# 3. Demande le mot de passe sudo (et le garde en cache)
# 4. Desactive la mise en veille pendant l'execution
# 5. Lance l'interface web et ouvre le navigateur
# 6. Reactive la mise en veille a la fermeture
#
# Usage: ./nobaraforgeKDE.sh
# =============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_SCRIPT="$SCRIPT_DIR/nobara_kde_forge.py"

# -- Couleurs --
RED='\033[1;31m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
RESET='\033[0m'

info()    { echo -e "${BLUE}[INFO]${RESET} $1"; }
ok()      { echo -e "${GREEN}[OK]${RESET} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${RESET} $1"; }
fail()    { echo -e "${RED}[ERREUR]${RESET} $1"; exit 1; }

# -- Mode --uninstall : retire les fichiers systeme deposes par NobaraForgeKDE --
if [ "${1:-}" = "--uninstall" ]; then
    echo ""
    echo -e "${BLUE}================================================${RESET}"
    echo -e "${GREEN}  NobaraForgeKDE - Desinstallation systeme${RESET}"
    echo -e "${BLUE}================================================${RESET}"
    echo ""
    info "Suppression des fichiers systeme deposes par NobaraForgeKDE."
    info "Les paquets installes ne sont PAS desinstalles (utilisez le rollback dans l'UI pour ca)."
    echo ""

    if ! sudo -v; then fail "Acces sudo requis."; fi

    _targets=(
        "/etc/sudoers.d/nobaraforgekde"
        "/etc/plasmalogin.conf.d/nobaraforgekde.conf"
        "/etc/sddm.conf.d/nobaraforgekde.conf"
        "/etc/tlp.d/01-nobaraforgekde.conf"
    )
    _removed=0
    for f in "${_targets[@]}"; do
        if [ -f "$f" ]; then
            sudo rm -f "$f" && { ok "Supprime : $f"; _removed=$((_removed+1)); } || warn "Echec : $f"
        fi
    done

    # Nettoyage logs et state
    if [ -d "$SCRIPT_DIR/logs" ] || [ -d "$SCRIPT_DIR/data" ]; then
        read -r -p "Supprimer aussi logs/ et data/state.json ? [y/N] " _ans
        if [ "${_ans,,}" = "y" ]; then
            rm -rf "$SCRIPT_DIR/logs" "$SCRIPT_DIR/data"
            ok "logs/ et data/ supprimes"
        fi
    fi

    ok "Desinstallation terminee ($_removed fichier(s) systeme retire(s))."
    exit 0
fi

echo ""
echo -e "${BLUE}================================================${RESET}"
echo -e "${GREEN}  NobaraForgeKDE - Lancement complet${RESET}"
echo -e "${BLUE}================================================${RESET}"
echo ""

# =============================================================
# 1. Verifier Python 3
# =============================================================
info "Verification de Python 3..."
command -v python3 &>/dev/null || fail "Python 3 non trouve. Installez-le avec: sudo dnf install python3"
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
ok "Python $PYTHON_VERSION"

# =============================================================
# 2. Verifier/installer uv
# =============================================================
if ! command -v uv &>/dev/null; then
    info "uv non trouve, installation..."
    _UV_DONE=0

    # Methode 1 : script officiel astral.sh
    if curl -LsSf https://astral.sh/uv/install.sh -o /tmp/_uv_install.sh 2>/dev/null; then
        sh /tmp/_uv_install.sh && _UV_DONE=1
        rm -f /tmp/_uv_install.sh
    else
        warn "Script officiel astral.sh indisponible, tentative via pip..."
    fi

    # Methode 2 : fallback pip
    if [ "$_UV_DONE" = "0" ]; then
        pip install --user uv --quiet 2>/dev/null \
            || pip3 install --user uv --quiet 2>/dev/null \
            || fail "Impossible d'installer uv. Essayez manuellement : pip install uv"
    fi

    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    command -v uv &>/dev/null || fail "uv introuvable apres installation (PATH: $PATH)"
    ok "uv installe ($(uv --version | cut -d' ' -f2))"
else
    ok "uv $(uv --version | cut -d' ' -f2)"
fi

# =============================================================
# 3. Synchroniser les dependances avec uv
# =============================================================
info "Synchronisation des dependances (uv sync)..."
uv sync --quiet || fail "uv sync a echoue. Verifiez pyproject.toml"
ok "Dependances synchronisees"

# Verification rapide de Flask via uv run
uv run python -c "import flask" 2>/dev/null || fail "Flask introuvable apres uv sync"

# =============================================================
# 4. Demander sudo (cache le mot de passe pour les scripts)
# =============================================================
echo ""
info "Verification de l'acces sudo..."
if ! sudo -v; then
    fail "Acces sudo requis pour installer les paquets."
fi
ok "Acces sudo"

# =============================================================
# 4b. Installer les outils requis si absents
# =============================================================
_MISSING_PKGS=()
command -v sassc   &>/dev/null || _MISSING_PKGS+=("sassc")
command -v acpi    &>/dev/null || _MISSING_PKGS+=("acpi")
command -v git     &>/dev/null || _MISSING_PKGS+=("git")
if [ ${#_MISSING_PKGS[@]} -gt 0 ]; then
    info "Installation des outils requis : ${_MISSING_PKGS[*]}..."
    sudo dnf install -y "${_MISSING_PKGS[@]}" \
        || warn "Impossible d'installer : ${_MISSING_PKGS[*]} (verifiez la connexion)"
    ok "Outils requis installes"
fi

# Configurer sudoers pour firewall-cmd sans mot de passe (temporaire — nettoye au quit)
SUDOERS_FILE="/etc/sudoers.d/nobaraforgekde"
SUDOERS_CREATED=0
if [ ! -f "$SUDOERS_FILE" ]; then
    info "Configuration sudo temporaire (firewall-cmd)..."
    {
        echo "# Genere par NobaraForgeKDE — supprime a la fermeture"
        echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/firewall-cmd"
    } | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 440 "$SUDOERS_FILE"
    SUDOERS_CREATED=1
    ok "Sudo configure (firewall-cmd sans mot de passe)"
fi

# Garder sudo actif en arriere-plan (renouvelle toutes les 50s)
(while true; do sudo -n true 2>/dev/null; sleep 50; done) &
SUDO_KEEPER_PID=$!

# =============================================================
# 5. Desactiver la mise en veille (KDE Plasma)
# =============================================================
INHIBIT_COOKIE=""

disable_sleep() {
    # KDE: utiliser qdbus pour inhiber la mise en veille
    if command -v qdbus &>/dev/null || command -v qdbus6 &>/dev/null; then
        QDBUS=$(command -v qdbus6 2>/dev/null || command -v qdbus 2>/dev/null)
        INHIBIT_COOKIE=$($QDBUS org.freedesktop.PowerManagement /org/freedesktop/PowerManagement/Inhibit \
            org.freedesktop.PowerManagement.Inhibit.Inhibit \
            "NobaraForgeKDE" "Installation en cours" 2>/dev/null || echo "")
        if [ -n "$INHIBIT_COOKIE" ]; then
            ok "Mise en veille inhibee (cookie: $INHIBIT_COOKIE)"
        else
            warn "Impossible d'inhiber la mise en veille via qdbus"
        fi
    # Fallback: systemd-inhibit
    elif command -v systemd-inhibit &>/dev/null; then
        warn "qdbus non disponible, mise en veille non inhibee automatiquement"
    fi
}

restore_sleep() {
    if [ -n "$INHIBIT_COOKIE" ]; then
        QDBUS=$(command -v qdbus6 2>/dev/null || command -v qdbus 2>/dev/null)
        $QDBUS org.freedesktop.PowerManagement /org/freedesktop/PowerManagement/Inhibit \
            org.freedesktop.PowerManagement.Inhibit.UnInhibit \
            "$INHIBIT_COOKIE" 2>/dev/null || true
        info "Mise en veille restauree"
    fi
}

disable_sleep

# =============================================================
# 6. Nettoyage a la fermeture (CTRL+C ou fin normale)
# =============================================================
cleanup() {
    echo ""
    info "Arret de NobaraForgeKDE..."
    restore_sleep
    kill "$SUDO_KEEPER_PID" 2>/dev/null
    if [ "$SUDOERS_CREATED" = "1" ] && [ -f "$SUDOERS_FILE" ]; then
        sudo -n rm -f "$SUDOERS_FILE" 2>/dev/null \
            && info "Sudoers temporaire nettoye" \
            || warn "Impossible de supprimer $SUDOERS_FILE (a faire manuellement)"
    fi
    ok "NobaraForgeKDE arrete. A bientot!"
}

trap cleanup EXIT

# =============================================================
# 7. Lancer l'application
# =============================================================
echo ""
echo -e "${BLUE}================================================${RESET}"
echo -e "${GREEN}  NobaraForgeKDE pret - Lancement...${RESET}"
echo -e "${BLUE}================================================${RESET}"
echo ""
info "URL: http://localhost:5000"
info "Arret: CTRL+C"
echo ""

uv run python "$PYTHON_SCRIPT"
