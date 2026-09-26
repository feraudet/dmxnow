# ADR 0005 — Relais de coupure Omron G5RL-1A-E-HR

**Statut :** Accepté (décision 5), amendé : G5RL-U1A-E remplacé par G5RL-1A-E-HR

## Contexte

Le nœud commute l'alimentation d'un projecteur LED (et d'une alimentation LED externe) dont les alimentations à découpage présentent de forts courants d'appel.

## Décision

Un relais Omron G5RL-1A-E-HR (LCSC C113250), bobine 5 V DC, contact NO 16 A, commandé par un MOSFET AO3400 depuis GPIO5, diode de roue libre 1N4148W.

## Conséquences

- Version « forts courants d'appel » : dimensionnée pour ~500 W de charges LED (à confirmer V-SYS-01).
- Contact NO : projecteur éteint si le nœud est hors tension ou planté au démarrage.
- Bobine ~0,4 W en permanence quand le projecteur est allumé.
- Intervalle minimal entre commutations (3 s) et persistance NVS limitée (SPEC §4.5).

## Alternatives écartées

- Relais statique (triac/SSR) : fuites, échauffement, mauvaise tenue aux charges capacitives.
- Relais 10 A standard : soudure des contacts à l'appel de courant.

## Amendement — G5RL-1A-E-HR

La référence initiale G5RL-U1A-E est la version **bistable** (verrouillage, deux bobines
set/reset) de la série G5RL : elle ne peut pas être commandée par un simple MOSFET et
conserve son dernier état sans alimentation, contrairement à l'objectif « projecteur éteint
si le nœud est hors tension ». Elle est remplacée par le **G5RL-1A-E-HR** (monostable, NO,
16 A 250 V AC, courant d'appel 100 A crête, isolation bobine-contacts renforcée 8 mm /
10 kV), vérifié sur le catalogue Omron G5RL p. 5 :

- implantation identique à l'empreinte déjà placée : bobine 1/8 (7,5 mm), COM 3/6 à 20 mm,
  NO 4/5 à 25 mm, trous 1,3 mm ;
- bobine 5 V : 80 mA, 62,5 Ω (≈ 400 mW), sans polarité ;
- disponible chez LCSC (C113250).

Choix validé par l'utilisateur. La variante -1A-E-TV8 (classe TV-8) reste une alternative à
même implantation si des charges capacitives plus sévères sont confirmées (V-SYS-01).
