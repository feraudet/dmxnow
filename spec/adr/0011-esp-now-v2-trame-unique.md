# ADR 0011 : ESP-NOW v2, un univers par paquet, plateforme pioarduino

**Statut :** Accepté (arbitrage A8, 2026-09-25)

## Contexte

ESP-NOW v1 limite la charge utile à 250 octets ; un univers en demande 530 avec l'en-tête. ESP-NOW v2 (1470 octets) exige ESP-IDF ≥ 5.4, donc Arduino-ESP32 ≥ 3.2, que la plateforme PlatformIO officielle ne fournit pas.

## Décision

Utiliser ESP-NOW v2 avec un paquet par univers, sur la plateforme communautaire pioarduino (versions épinglées). Implémenter aussi un mode fragmenté v1 (3 paquets) sélectionnable sur le dongle.

## Conséquences

- Pas de déchirure entre fragments, pas de réassemblage en mode nominal, temps d'antenne ~0,9 ms contre ~1,6 ms, perte par univers divisée par ~3.
- Dépendance à une plateforme communautaire (risque R-05) ; le code `common` reste indépendant d'Arduino pour permettre un repli ESP-IDF pur.

## Alternatives écartées

- v1 fragmenté seul sur la plateforme officielle (Arduino 2.x, IDF 4.4) : fonctionne mais moins robuste.
- ESP-IDF pur sans Arduino : plus de code (page de maintenance, OTA).
