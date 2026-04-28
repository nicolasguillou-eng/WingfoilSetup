from datetime import datetime

# ---------- CONSTANTES ----------
DIRECTIONS_VALIDES = {
    "N", "NNE", "NE", "ENE",
    "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW",
    "W", "WNW", "NW", "NNW"
}

DIRECTIONS_OFFSHORE = {"S", "SSW", "SW", "WSW"}
DIRECTIONS_WAVES    = {"W", "WNW", "NW", "SW", "SSW", "S"}

# ---------- FACTEUR SAISONNIER ----------
def facteur_saison(mois: int = None) -> float:
    if mois is None:
        mois = datetime.now().month
    if mois in (3, 4, 5):
        return 0.9
    elif mois in (6, 7, 8):
        return 1.0
    elif mois in (9, 10, 11):
        return 1.05
    else:
        return 1.1

# ---------- UTILITAIRES POUR LISTE UNIQUE DE MATOS ----------
def extraire_items(valeur: str) -> list[str]:
    if not isinstance(valeur, str):
        return []
    for sep in [" ou ", " / "]:
        if sep in valeur:
            return [item.strip() for item in valeur.split(sep)]
    return [valeur.strip()]

def generer_liste_materiel_unique(setup1: dict, setup2: dict) -> dict:
    categories = ["foil", "wing", "board", "stab"]
    materiel = {}
    for cat in categories:
        items = set()
        for setup in (setup1, setup2):
            valeur = setup.get(cat, "")
            for item in extraire_items(valeur):
                if item:
                    items.add(item)
        materiel[cat] = sorted(items)
    return materiel

# ---------- VENT EFFECTIF (moyenne + rafale) ----------
def calculer_vent_effectif(vitesse_moyenne: float, rafale_max: float) -> tuple[float, float]:
    """
    Retourne (vent_effectif, ratio_rafale)
    vent_effectif = (vitesse_moyenne + rafale_max) / 2  (énergie moyenne)
    ratio_rafale = rafale_max / vitesse_moyenne (si moyenne>0)
    """
    if vitesse_moyenne <= 0:
        return rafale_max, 1.0
    ratio = rafale_max / vitesse_moyenne
    # Sécurité : si rafale très supérieure à la moyenne, on pénalise un peu
    # mais on garde une valeur représentative de l'effort moyen
    vent_effectif = (vitesse_moyenne + rafale_max) / 2
    return vent_effectif, ratio

# ---------- SETUPS DE BASE (PERF + FREERIDE) ----------
def calculer_setups_base(vent_effectif: float) -> tuple[dict, dict]:
    """
    Utilise le vent effectif (moyenne + rafale pondérée) pour choisir les gammes.
    """
    if vent_effectif < 10:
        perf = {
            "foil": "DW900", "wing": "7m CWC", "board": "96L",
            "stab": "S192", "mast": +2.5, "shim": +0.5,
            "note": "Pompe agressive pour décoller"
        }
        freeride = {
            "foil": "DW1400", "wing": "7m CWC", "board": "130L",
            "stab": "S192", "mast": +4.0, "shim": +0.8,
            "note": "Décollage le plus facile possible"
        }

    elif vent_effectif < 15:
        perf = {
            "foil": "DW900", "wing": "4.8m", "board": "96L",
            "stab": "S192", "mast": +1.5, "shim": +0.4,
            "note": "4.8 rigide = réactivité dès le décollage"
        }
        freeride = {
            "foil": "DW1400 ou DW900", "wing": "5m", "board": "130L",
            "stab": "S192", "mast": +3.0, "shim": +0.7,
            "note": "5m souple = montée facile, solide"
        }

    elif vent_effectif < 20:
        perf = {
            "foil": "HA1050", "wing": "4.8m", "board": "96L",
            "stab": "S192", "mast": +1.0, "shim": +0.2,
            "note": "HA1050 polyvalent : perf et wave riding – excellent équilibre"
        }
        freeride = {
            "foil": "DW900", "wing": "5m", "board": "96L",
            "stab": "S192", "mast": +1.5, "shim": +0.3,
            "note": "5m souple = lift confortable, vagues"
        }

    elif vent_effectif < 25:
        perf = {
            "foil": "HA550", "wing": "4.8m", "board": "96L",
            "stab": "S142", "mast": -1.0, "shim": -0.2,
            "note": "4.8 race + petit foil = vitesse max"
        }
        freeride = {
            "foil": "HA750", "wing": "5m", "board": "96L",
            "stab": "S192", "mast": +0.5, "shim": 0.0,
            "note": "5m souple + grand foil = confort"
        }

    elif vent_effectif < 30:
        perf = {
            "foil": "HA550", "wing": "4.8m", "board": "96L",
            "stab": "S142", "mast": -3.0, "shim": -0.6,
            "note": "4.8 rigide, contrôle dans le vent fort"
        }
        freeride = {
            "foil": "HA750", "wing": "5m", "board": "96L",
            "stab": "S142", "mast": -1.0, "shim": -0.2,
            "note": "5m souple, plus de stabilité en rafales"
        }

    else:  # >= 30 kts effectif
        perf = {
            "foil": "HA550", "wing": "3.5m", "board": "96L",
            "stab": "S142", "mast": -4.0, "shim": -0.8,
            "note": "Conditions costaud, pur contrôle"
        }
        freeride = {
            "foil": "HA750", "wing": "5m / 3.5m", "board": "96L",
            "stab": "S142", "mast": -2.0, "shim": -0.4,
            "note": "5m souple si gérable, sinon 3.5m"
        }

    return perf, freeride

# ---------- MODIFICATEUR INSTABILITÉ (rafales) ----------
def appliquer_modificateur_instabilite(setup: dict, ratio_rafale: float, vent_effectif: float) -> dict:
    """
    Si le vent est très instable (ratio > 1.6), on ajuste pour plus de sécurité :
    - Aile plus petite ou plus souple
    - Foil légèrement plus petit ou plus stable
    - Mast plus négatif pour déjauger
    """
    if ratio_rafale >= 1.6:
        # On ne modifie que si ce n'est pas déjà du très petit matos
        if "3.5m" not in setup["wing"] and "4.8m" in setup["wing"]:
            setup["wing"] = setup["wing"].replace("4.8m", "4.2m (rafales)")
            setup["note"] += " ⚡ Vent très instable → aile réduite"
        elif "5m" in setup["wing"] and "3.5m" not in setup["wing"]:
            setup["wing"] = setup["wing"].replace("5m", "4.2m")
            setup["note"] += " ⚡ Rafales fortes → aile plus petite"
        # Ajustement du foil si nécessaire (ex: HA750 → HA550)
        if "HA750" in setup["foil"] and vent_effectif > 18:
            setup["foil"] = setup["foil"].replace("HA750", "HA550")
            setup["note"] += " / foil réduit pour la stabilité"
        # Mast plus négatif pour moins de portance
        if "mast" in setup:
            setup["mast"] = setup["mast"] - 1.0
            setup["shim"] = setup["shim"] - 0.2
    return setup

# ---------- MODIFICATEUR OFFSHORE ----------
def appliquer_modificateur_offshore(setup: dict, vent_effectif: float) -> dict:
    if vent_effectif >= 25:
        setup["foil"] = "HA750 (offshore) ou HA550"
        setup["mast"] = -1.5
        setup["shim"] = -0.3
    elif vent_effectif < 15:
        setup["foil"] = "DW1400 ou DW900"
        setup["stab"] = "S192"
        setup["mast"] = +4.0
        setup["shim"] = +0.8
    return setup

# ---------- OVERRIDE VAGUES (avec HA1050) ----------
def appliquer_override_vagues(setup: dict, perf: bool = False) -> dict:
    setup["foil"] = "HA1050"
    setup["wing"] = "4.8m" if perf else "5m"
    setup["stab"] = "S142"
    setup["shim"] = -0.4
    setup["note"] = ("HA1050 – top perf et wave riding : précis, vivant et solide"
                     if perf else
                     "HA1050 – top wave riding : lift doux, tolérence et accroche en vagues")
    return setup

# ---------- AFFICHAGE D'UN SETUP ----------
def afficher_setup(label: str, emoji: str, setup: dict):
    width = 42
    print(f"\n{'─' * width}")
    print(f"  {emoji}  {label}")
    print(f"{'─' * width}")
    print(f"  Foil   : {setup['foil']}")
    print(f"  Wing   : {setup['wing']}")
    print(f"  Board  : {setup['board']}")
    print(f"  Stab   : {setup['stab']}")
    print(f"  Mast   : {setup['mast']:+.1f} cm  (+ avant/contrôle, – arrière/vitesse)")
    print(f"  Shim   : {setup['shim']:+.2f}°")
    if setup.get("note"):
        print(f"  💬 {setup['note']}")

# ---------- SESSION INTERACTIVE ----------
def session_interactive():
    print("╔══════════════════════════════════════════╗")
    print("║       WINGFOIL SETUP DU JOUR             ║")
    print("╚══════════════════════════════════════════╝\n")

    # 1. Vent moyen
    while True:
        try:
            vitesse_moy = float(input("Vitesse du vent MOYENNE (nœuds) : "))
            if vitesse_moy < 0:
                print("La vitesse doit être positive.")
                continue
            break
        except ValueError:
            print("Entrez un nombre valide.")

    # 2. Rafale max
    while True:
        try:
            rafale_max = float(input("Vitesse max des RAFALES (nœuds) : "))
            if rafale_max < vitesse_moy:
                print("La rafale max ne peut pas être inférieure à la moyenne. Réessayez.")
                continue
            break
        except ValueError:
            print("Entrez un nombre valide.")

    # 3. Direction
    while True:
        direction = input(
            f"Direction ({'/'.join(sorted(DIRECTIONS_VALIDES))}) : "
        ).strip().upper()
        if direction in DIRECTIONS_VALIDES:
            break
        print("Direction invalide. Ex : N, NE, SW, W…")

    # --- Calculs ---
    mois      = datetime.now().month
    coeff     = facteur_saison(mois)
    vent_effectif, ratio_rafale = calculer_vent_effectif(vitesse_moy, rafale_max)
    vent_ajuste = vent_effectif * coeff   # on applique le coefficient saisonnier sur le vent effectif

    # Avertissements
    warnings = []
    if vent_ajuste > 40:
        warnings.append("⚠️  VENT FORT > 40 nds effectifs — sortie à évaluer selon conditions et niveau.")
    if vent_ajuste <= 9 and direction in {"S", "SSW", "SSE", "SW", "SE"}:
        warnings.append("⚠️  Composante S ≤ 9 nds — déco difficile, prévoir pompage intense.")
    if ratio_rafale >= 1.6:
        warnings.append(f"🌬️  INDICE DE RAFALE ÉLEVÉ ({ratio_rafale:.2f}) → vent très instable, privilégier setup sécuritaire (aile plus petite / foil stable).")

    spot = _choisir_spot(direction)
    setup_perf, setup_freeride = calculer_setups_base(vent_ajuste)

    # Modificateur instabilité (rafales)
    setup_perf     = appliquer_modificateur_instabilite(setup_perf, ratio_rafale, vent_ajuste)
    setup_freeride = appliquer_modificateur_instabilite(setup_freeride, ratio_rafale, vent_ajuste)

    # Modificateurs offshore
    if direction in DIRECTIONS_OFFSHORE:
        setup_perf     = appliquer_modificateur_offshore(setup_perf, vent_ajuste)
        setup_freeride = appliquer_modificateur_offshore(setup_freeride, vent_ajuste)

    # Override vagues (utilise HA1050)
    if direction in DIRECTIONS_WAVES and vent_ajuste >= 15:
        setup_perf     = appliquer_override_vagues(setup_perf, perf=True)
        setup_freeride = appliquer_override_vagues(setup_freeride, perf=False)

    # --- Affichage ---
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    for w in warnings:
        print(f"\n{w}")
    print(f"\n📅  {date_str}")
    print(f"🌬️   VENT MOYEN : {vitesse_moy} nds  |  RAFALE MAX : {rafale_max} nds")
    print(f"   → Vent effectif : {vent_effectif:.1f} nds  |  Ajusté saison : {vent_ajuste:.1f} nds (coeff {coeff})")
    print(f"   → Indice rafale : {ratio_rafale:.2f}  {'(instable)' if ratio_rafale>=1.6 else '(stable)'}")
    print(f"🏖️   SPOT : {spot}")

    afficher_setup("SETUP 1 — PERF",          "🚀", setup_perf)
    afficher_setup("SETUP 2 — FREERIDE / CONFORT", "🛋️", setup_freeride)

    # --- Résumé du matériel unique à emporter ---
    materiel_unique = generer_liste_materiel_unique(setup_perf, setup_freeride)
    print(f"\n{'─' * 42}")
    print("  🧰  MATÉRIEL À EMBARQUER (unique)")
    print(f"{'─' * 42}")
    for cat, items in materiel_unique.items():
        if items:
            print(f"  {cat.capitalize()} : {', '.join(items)}")
        else:
            print(f"  {cat.capitalize()} : —")
    print(f"\n{'─' * 42}")

# ---------- HELPER SPOT ----------
def _choisir_spot(direction: str) -> str:
    if direction in DIRECTIONS_WAVES:
        return "Kervel / Trezmalaouen"
    elif direction in {"W", "WNW", "NW"}:
        return "Sables Blancs / Crozon"
    elif direction in {"N", "NNE", "NNW"}:
        return "Sables Blancs"
    elif direction in DIRECTIONS_OFFSHORE:
        return "Kervel / Trezmalaouen"
    else:
        return "Sables Blancs"

# ---------- EXÉCUTION ----------
if __name__ == "__main__":
    session_interactive()