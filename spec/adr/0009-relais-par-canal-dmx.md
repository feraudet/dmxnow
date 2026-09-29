# ADR 0009 : Commande du relais par un canal DMX

**Statut :** Accepté (décision 9)

## Contexte

L'opérateur veut allumer et éteindre les appareils depuis QLC+ comme n'importe quel paramètre.

## Décision

Le canal `start_address` de l'univers pilote le relais (≥ 128 = allumé), activable par `relay_dmx`. Forçage possible par commande ESP-NOW (prioritaire, non persistant), anti-rebond différé de 3 s.

## Conséquences

- Pas d'outil spécifique pour allumer une installation.
- Un nœud consomme 1 canal (projecteur seul), 5 ou 9 canaux (rubans 8 ou 16 bits).
- Règles de priorité SPEC §4.5.

## Alternatives écartées

- Commande uniquement par la CLI : hors de la conduite QLC+.
