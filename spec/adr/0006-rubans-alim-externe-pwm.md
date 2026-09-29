# ADR 0006 : Rubans LED : alimentation externe, 4 PWM côté masse

**Statut :** Accepté (décision 6)

## Contexte

Piloter des rubans 12/24 V jusqu'à ~200 W sans rendre le boîtier volumineux.

## Décision

L'alimentation 12/24 V (Mean Well LRS ou HLG) reste externe, alimentée par la sortie commutée J4b. Le nœud fournit 4 canaux PWM côté masse (MOSFET AOD4184A commandés en 5 V par un 74AHCT125).

## Conséquences

- Boîtier compact, pas de dissipation de l'alimentation dans le nœud.
- Rubans éteints par le relais (via l'alimentation) ou par PWM à 0 : pas de commande indépendante.
- Chemin 17 A, fusible 20 A, TVS et capacité d'entrée sur la partie sécable ; déphasage des PWM pour réduire l'ondulation (SPEC §4.6).

## Alternatives écartées

- Alimentation intégrée : taille, thermique, homologation.
- Commande côté + (P-MOSFET) : plus complexe, inutile pour des rubans à anode commune.
