# ADR 0007 : PCB unique sécable (V-cut remplacé par des languettes perforées)

**Statut :** Accepté (décision 7), amendé le 2026-09-26 : languettes perforées au lieu du V-cut

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

## Amendement (2026-09-26) : languettes perforées

La revue de conception de la rév. 0.2 a montré que le V-cut était inutilisable :

- une rainure V entaille les **deux faces** d'une carte ; sur un circuit 2 couches, les
  pistes qui traversent la ligne (PWM1-4, BOARD_SENSE, +5V, GND) auraient été coupées dès la
  fabrication, et la carte entière n'aurait pas fonctionné ;
- JLCPCB n'accepte le V-cut que sur des panneaux d'au moins 70 × 70 mm (carte de 54 mm de
  haut).

Décision (validée par l'utilisateur) : repli prévu au risque R-14. Fente fraisée de 2 mm à
X = 100 mm et trois languettes pleines (5, 7,5 et 11 mm, minimum JLCPCB 5 mm) portant les
sept pistes ; une rangée de trous NPTH de 0,5 mm au pas de 0,75 mm, interrompue au passage
des pistes, affaiblit la ligne de rupture. Les pistes ne se coupent qu'au moment où l'on
casse la partie rubans. Tout reste dans les Gerbers (Edge.Cuts et perçages NPTH) : plus de
calque V-cut à transmettre.

Conséquences : bords légèrement dentelés après rupture (à ébavurer), languettes plus
difficiles à casser qu'un V-cut (pince plate, en pliant vers la face arrière).

