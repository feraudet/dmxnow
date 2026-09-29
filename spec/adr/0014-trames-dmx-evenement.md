# ADR 0014 : Émission DMX sur événement et longueur de trame configurable

**Statut :** Accepté (arbitrage A3 : défaut 512, 2026-09-25)

## Contexte

Une trame DMX de 512 canaux dure 22,7 ms : un rafraîchissement à cadence fixe ajoute jusqu'à 23 ms de latence, incompatible avec l'objectif < 10 ms.

## Décision

Le nœud démarre une trame DMX dès qu'une nouvelle trame radio arrive (sinon toutes les 22,7 ms) et émet `dmx_out_slots` canaux (24 à 512). Même règle d'émission sur événement au dongle.

## Conséquences

- Latence typique ~3 ms avec des trames courtes ; ~13 ms avec 512 canaux (SPEC §5.1).
- Certains appareils anciens supportent mal les trames courtes : valeur par défaut soumise à A3.

## Alternatives écartées

- Cadence fixe 44 Hz : simple, latence élevée.
