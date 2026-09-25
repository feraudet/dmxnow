# ADR 0008 — Borniers WAGO série 2604

**Statut :** Accepté (décision 8)

## Contexte

Raccordements utilisateur 230 V et 12/24 V fréquents, parfois sur le terrain, sans outil.

## Décision

Bornes à levier pour circuit imprimé WAGO 2604 (4 mm², pas 5 mm) pour J1, J4, J4b, J5, J6. La double sortie secteur est réalisée par une seconde borne J4b en parallèle de J4 (une seule âme par point de serrage).

## Conséquences

- Raccordement sans outil, fiable, visible.
- Coût notable (poste principal de la BOM).
- Références exactes et caractéristiques à confirmer sur la fiche WAGO (V-HW-04).

## Alternatives écartées

- Borniers à vis : serrage variable, moins pratique.
- Connecteurs débrochables : coût, risque d'erreur de raccordement.
