# ADR 0003 — Microcontrôleur ESP32-C3-MINI-1

**Statut :** Accepté (décision 3)

## Contexte

Le nœud a besoin d'une radio ESP-NOW, d'un UART pour le DMX, de 4 PWM, d'une broche relais et d'une mise à jour OTA.

## Décision

Module ESP32-C3-MINI-1 (flash intégrée, antenne PCB intégrée), programmation par l'USB natif (GPIO18/19).

## Conséquences

- Module précertifié radio : pas de conception RF.
- Zone d'exclusion d'antenne à respecter sur le PCB et le boîtier.
- GPIO limités (IO0-IO10, IO18-21) : affectation SPEC §4.2 ; IO2/IO8/IO9 sont des broches de strapping.
- BOOT (IO9) à la masse au reset entre dans le chargeur ROM : l'entrée en maintenance par BOOT est reformulée (SPEC §4.2).

## Alternatives écartées

- ESP32 classique (WROOM) : plus gros, plus gourmand, pas d'USB natif.
- ESP32-C3-MINI-1U (antenne externe) : connecteur et antenne à loger dans le boîtier.
