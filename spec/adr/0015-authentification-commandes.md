# ADR 0015 : Authentification des commandes par HMAC tronqué

**Statut :** Accepté (arbitrage A4, 2026-09-25)

## Contexte

`MAINTENANCE` ouvre un point d'accès et l'OTA ; `RELAY` et `FACTORY_RESET` agissent sur l'installation. Le `net_id` circule en clair et le broadcast ESP-NOW ne peut pas être chiffré.

## Décision

Remorque de 12 octets (compteur 32 bits + HMAC-SHA256 tronqué à 8 octets) sur les COMMAND, clé de 32 octets partagée entre le Pi et les nœuds, anti-rejeu par compteur croissant, enrôlement sans clé (confiance au premier usage). DMX_DATA non authentifié.

## Conséquences

- Protège contre les commandes accidentelles d'une autre installation et les attaques simples.
- Gestion d'une clé à sauvegarder (perte ⇒ `FACTORY_RESET` par action locale).
- Coût négligeable (commandes rares, SHA-256 matériel sur ESP32-C3).

## Alternatives écartées

- Aucune authentification : plus simple, suffisant si l'installation est isolée.
- Chiffrement ESP-NOW unicast (CCMP) : impossible en broadcast, limité à quelques pairs chiffrés.
