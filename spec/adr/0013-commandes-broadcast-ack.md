# ADR 0013 — Commandes en broadcast avec acquittement applicatif

**Statut :** Proposé

## Contexte

Les commandes ne sont pas périodiques ; il faut garantir leur exécution unique.

## Décision

Le dongle émet les commandes en broadcast avec la MAC cible dans la charge utile ; le nœud acquitte en unicast ; le dongle retransmet jusqu'à 5 fois (30 à 240 ms) ; le nœud déduplique par `cmd_id` (16 derniers) et renvoie l'ACK mémorisé.

## Conséquences

- Le dongle n'a pas à gérer la table de pairs ESP-NOW (limitée à 20) pour chaque nœud.
- Même mécanisme pour une cible ou tous les nœuds.
- Exécution au plus une fois, acquittement au moins une fois.

## Alternatives écartées

- Unicast ESP-NOW vers chaque nœud : acquittement MAC natif mais gestion dynamique des pairs.
- Répétition aveugle sans ACK : pas de retour d'état fiable.
