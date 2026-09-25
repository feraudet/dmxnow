# ADR 0007 — PCB unique sécable par V-cut

**Statut :** Accepté (décision 7)

## Contexte

Deux variantes (projecteur seul, projecteur + rubans) sans multiplier les références de carte.

## Décision

Une carte ~130 × 50 mm avec V-cut vertical : partie principale ~90 × 50 mm toujours conservée, partie rubans détachable. Seuls PWM1-4, BOARD_SENSE, +5V et GND traversent la découpe.

## Conséquences

- Une seule fabrication, variante choisie au montage.
- Détection automatique de variante (BOARD_SENSE).
- Aucun 230 V ne traverse ni n'approche la découpe (4 mm de chaque côté).
- À vérifier : acceptation du V-cut sur une carte unique de 50 mm chez JLCPCB (V-HW-12).

## Alternatives écartées

- Deux PCB distincts : double gestion.
- Carte fille connectée : connecteur supplémentaire, coût.
