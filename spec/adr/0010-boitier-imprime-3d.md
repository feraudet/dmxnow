# ADR 0010 : Boîtier imprimé 3D paramétrique

**Statut :** Accepté (décision 10)

## Contexte

Petite série, deux longueurs, besoin de cloison 230 V et d'arrêts de traction.

## Décision

Modèle CadQuery unique générant les deux variantes, en matériau ignifugé (ABS-FR V-0 recommandé, SPEC §4.12), inserts M3 à chaud, couvercle d'accès aux borniers vissé.

## Amendement (2026-09-26, livrable 8.6)

- Géométrie issue de `enclosure/board.json` (export du PCB) plutôt que d'un STEP.
- Chambres de câblage aux extrémités pour les presse-étoupes et les étriers : 208 × 72 × 34 mm
  (carte entière), 145 × 72 × 34 mm (cassée), au-delà de l'objectif ENF-05, qui n'était
  qu'indicatif. Réduire la longueur supposerait de renoncer à l'étrier indépendant (ES-05)
  ou aux presse-étoupes : non retenu ; taille acceptée par l'utilisateur le 2026-09-27.
- Cloison en trois parties (fond, languettes dans les fentes, jupe du couvercle 230 V).

## Conséquences

- Adaptation facile ; exports STL/STEP versionnés.
- La classification au feu dépend du filament et des paramètres d'impression (V-ENC-02).

## Alternatives écartées

- Boîtier du commerce : pas de cloison ni de passages adaptés.
- PETG/ABS standard : classés HB, insuffisants pour une enveloppe contenant du secteur.
