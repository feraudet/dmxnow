# ADR 0005 — Relais de coupure Omron G5RL-U1A-E

**Statut :** Accepté (décision 5)

## Contexte

Le nœud commute l'alimentation d'un projecteur LED (et d'une alimentation LED externe) dont les alimentations à découpage présentent de forts courants d'appel.

## Décision

Un relais Omron G5RL-U1A-E, bobine 5 V DC, contact NO 16 A, commandé par un MOSFET AO3400 depuis GPIO5, diode de roue libre 1N4148W.

## Conséquences

- Version « forts courants d'appel » : dimensionnée pour ~500 W de charges LED (à confirmer V-SYS-01).
- Contact NO : projecteur éteint si le nœud est hors tension ou planté au démarrage.
- Bobine ~0,4 W en permanence quand le projecteur est allumé.
- Intervalle minimal entre commutations (3 s) et persistance NVS limitée (SPEC §4.5).

## Alternatives écartées

- Relais statique (triac/SSR) : fuites, échauffement, mauvaise tenue aux charges capacitives.
- Relais 10 A standard : soudure des contacts à l'appel de courant.
