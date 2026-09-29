# ADR 0012 : Liaison série Pi ↔ dongle encadrée COBS + CRC16

**Statut :** Accepté (validation de la spec, 2026-09-25)

## Contexte

Le cahier des charges demande COBS ou SLIP avec CRC.

## Décision

COBS avec délimiteur 0x00 et CRC-16/CCITT-FALSE (PROTOCOL §8).

## Conséquences

- Surcoût borné (≤ 3 octets par univers) et déterministe, contre jusqu'à ×2 pour SLIP sur des données DMX arbitraires.
- Resynchronisation immédiate sur le prochain 0x00.
- Même CRC que la radio : un seul code.

## Alternatives écartées

- SLIP : surcoût variable selon les données.
- Longueur préfixée sans délimiteur : resynchronisation difficile après erreur.
