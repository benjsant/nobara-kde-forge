"""Detection de PC portable via sysfs (pas de paquet externe requis)."""
from pathlib import Path

_DMI_DIR = Path("/sys/class/dmi/id")


def _dmi(field):
    """Lit un champ DMI (ex: sys_vendor, product_name). Vide si absent."""
    f = _DMI_DIR / field
    if not f.exists():
        return ""
    try:
        return f.read_text().strip()
    except Exception:
        return ""


def is_laptop():
    """Detecte un laptop par la presence d'une batterie dans /sys/class/power_supply/.
    Retourne (bool, dict) : (est_laptop, infos_batterie + vendor/product)."""
    power_supply = Path("/sys/class/power_supply")
    if not power_supply.exists():
        return False, {}
    for supply in sorted(power_supply.iterdir()):
        type_file = supply / "type"
        if type_file.exists() and type_file.read_text().strip() == "Battery":
            info = {"name": supply.name}
            for key in ("capacity", "status", "cycle_count"):
                f = supply / key
                if f.exists():
                    val = f.read_text().strip()
                    info[key] = int(val) if val.isdigit() else val
            vendor = _dmi("sys_vendor")
            if vendor:
                info["vendor"] = vendor
                info["product"] = _dmi("product_name")
                info["vendor_id"] = _vendor_id(vendor)
            return True, info
    return False, {}


def _vendor_id(vendor):
    """Normalise le vendor DMI en id stable : 'asus', 'lenovo', 'dell', 'hp', 'msi', 'framework', 'other'."""
    v = vendor.lower()
    if "asus" in v:
        return "asus"
    if "lenovo" in v:
        return "lenovo"
    if "dell" in v:
        return "dell"
    if "hewlett" in v or v.startswith("hp "):
        return "hp"
    if "micro-star" in v or "msi" in v:
        return "msi"
    if "framework" in v:
        return "framework"
    if "acer" in v:
        return "acer"
    if "razer" in v:
        return "razer"
    return "other"


def is_asus_laptop():
    """Helper rapide : True si laptop ASUS detecte (pour proposer asusctl)."""
    detected, info = is_laptop()
    return detected and info.get("vendor_id") == "asus"
