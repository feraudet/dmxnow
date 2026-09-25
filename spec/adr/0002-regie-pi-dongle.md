# ADR 0002 — Régie Raspberry Pi + QLC+ + dongle XIAO ESP32-C3

**Statut :** Accepté (décision 2)

## Contexte

La régie est un Raspberry Pi sous QLC+. Le Pi n'a pas de radio compatible ESP-NOW.

## Décision

QLC+ émet de l'Art-Net vers 127.0.0.1 ; un démon Python (`dmxnowd`) le reçoit, répond aux ArtPoll et transmet les univers en USB à un dongle Seeed XIAO ESP32-C3 qui les diffuse en ESP-NOW.

## Conséquences

- Aucune modification de QLC+ : la sortie Art-Net standard suffit.
- Le démon est le point unique pour la supervision (heartbeats) et les commandes (CLI).
- Même famille de puce que les nœuds : code `common` partagé.
- Point de défaillance unique (dongle) : le dongle continue d'émettre la dernière trame pendant `hold_timeout` si le Pi se tait.

## Alternatives écartées

- Plugin QLC+ natif : maintenance lourde, couplage à une version de QLC+.
- Dongle Wi-Fi du Pi en mode moniteur/injection pour émettre de l'ESP-NOW : fragile, dépendant du pilote.
