# ADR 0008 — Borniers WAGO série 2604

**Statut :** Accepté (décision 8), amendé par l'arbitrage A9 (2026-09-26)

## Contexte

Raccordements utilisateur 230 V et 12/24 V fréquents, parfois sur le terrain, sans outil.

## Décision

Bornes à levier pour circuit imprimé WAGO 2604 (4 mm², pas 5 mm) pour J1, J4, J4b, J5, J6. La double sortie secteur est réalisée par une seconde borne J4b en parallèle de J4 (une seule âme par point de serrage).

## Amendement A9

Le routage 16 A en 2 couches avec trois borniers 3 pôles s'est révélé infaisable proprement (pistes de pôles voisins au pas de 5 mm, croisements L/N/PE). J1, J4 et J4b deviennent des WAGO 2604-1102 (L, N) ; les trois PE sont réunis hors carte par un WAGO 221-413 dans le compartiment 230 V.

## Amendement J6 (2026-09-26)

Le 2604-1105 (5 pôles) prévu pour les sorties rubans est arrêté chez WAGO (page produit « Discontinued ») et à 0 en stock chez JLCPCB/LCSC. Il est remplacé par deux blocs en stock : **J6 2604-1102** (VLED, CH1) et **J8 2604-1103** (CH2 à CH4), choisis pour la profondeur de stock et parce que le 2604-1102 est déjà la référence de J1, J4, J4b et J5. D'après la fiche (L = (n − 1) × 5 + 7,4 mm), deux blocs côte à côte imposent 7,4 mm entre leurs broches voisines ; le PCB prévoit 8,0 mm (CH1 → CH2). Alternatives écartées : 2604-1104 + 2604-1101 (repérage plus lisible, mais 47 pièces de 2604-1104 en stock) ; 2604-1106 (26 pièces, pôle inutile qui ne tient pas entre H3 et C8).

## Conséquences

- Raccordement sans outil, fiable, visible.
- Coût notable (poste principal de la BOM).
- Références exactes et caractéristiques à confirmer sur la fiche WAGO (V-HW-04).

## Alternatives écartées

- Borniers à vis : serrage variable, moins pratique.
- Connecteurs débrochables : coût, risque d'erreur de raccordement.
