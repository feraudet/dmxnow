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

## Amendement (2026-10-13, maquette PLA)

- **Un seul couvercle** au lieu d'un couvercle 230 V et d'un couvercle basse tension, à
  la demande de l'utilisateur. ES-05 reste tenue : les borniers secteur ne sont
  accessibles qu'après avoir dévissé le couvercle. Ouvrir le côté rubans découvre
  désormais aussi le côté secteur : l'intervention se fait fiche débranchée, comme toute
  ouverture du boîtier ([docs/securite.md](../../docs/securite.md)).
- Le rebord de centrage du couvercle 230 V appuyait sur la cloison et empêchait la
  fermeture : encoche au-dessus de la cloison, et contrôle couvercle contre fond ajouté à
  `make check`.
- Trous de presse-étoupes M16 16,8 mm, M12 12,8 mm, ergot H1 2,6 mm (jeux FDM).

## Conséquences

- Adaptation facile ; exports STL/STEP versionnés.
- La classification au feu dépend du filament et des paramètres d'impression (V-ENC-02).

## Alternatives écartées

- Boîtier du commerce : pas de cloison ni de passages adaptés.
- PETG/ABS standard : classés HB, insuffisants pour une enveloppe contenant du secteur.
