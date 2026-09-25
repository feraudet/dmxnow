# ADR 0010 — Boîtier imprimé 3D paramétrique

**Statut :** Accepté (décision 10)

## Contexte

Petite série, deux longueurs, besoin de cloison 230 V et d'arrêts de traction.

## Décision

Modèle CadQuery unique générant les deux variantes, en matériau ignifugé (ABS-FR V-0 recommandé, SPEC §4.12), inserts M3 à chaud, couvercle d'accès aux borniers vissé.

## Conséquences

- Adaptation facile ; exports STL/STEP versionnés.
- La classification au feu dépend du filament et des paramètres d'impression (V-ENC-02).

## Alternatives écartées

- Boîtier du commerce : pas de cloison ni de passages adaptés.
- PETG/ABS standard : classés HB, insuffisants pour une enveloppe contenant du secteur.
