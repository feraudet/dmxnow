# ADR 0018 : Un seul firmware pour les cartes nœud, rôle nœud ou dongle

**Statut :** Accepté (demande de l'utilisateur, 2026-10-15)

## Contexte

Jusqu'ici, une carte nœud recevait `firmware/node` et la XIAO recevait
`firmware/dongle`. En attendant la XIAO, la carte n°2 (…C5:98) a été flashée avec le
firmware du dongle : elle ne pouvait plus servir de nœud sans être reflashée.
L'utilisateur veut que chaque carte ait le même firmware, et qu'une procédure simple la
fasse passer de nœud à dongle et inversement : toute carte doit pouvoir servir de
dongle, branchée en USB.

Choix faits avec lui le 2026-10-15 :

- bascule automatique quand le démon parle à la carte sur l'USB, **et** commande
  `dmxnow role` ;
- la XIAO garde son firmware à part ;
- en dongle, la carte sort aussi son univers sur sa XLR ;
- 🔴 une carte en rôle dongle n'est jamais raccordée au secteur.

## Décision

- L'application du dongle devient une bibliothèque, `firmware/dongle_app`, avec des
  points d'accroche (sonde de latence, carte, origine du rôle, univers reçus, demande de
  rôle). `firmware/dongle` (XIAO) et `firmware/node` (cartes nœud) l'utilisent.
- Au démarrage, `boot_role()` (`firmware/common`, testée sur poste) choisit le rôle
  d'après le rôle enregistré en NVS (clé `role`, hors du bloc de configuration) et un
  drapeau en mémoire RTC.
- Bascule automatique sans redémarrage, au premier `PING` valide reçu sur l'USB. Un
  redémarrage serait fragile : l'ouverture du port par l'hôte peut réinitialiser la puce.
- Rôle enregistré par la commande radio `SET_ROLE` (0x0F, authentifiée, refusée sans
  clé réseau). Retour au nœud par le message série `SET_ROLE` (0x06) ou `FACTORY_RESET`.
- Le `STATUS` du dongle indique la carte et l'origine du rôle.

## Conséquences

- Une seule image pour toutes les cartes nœud : `dmxnow ota` et le flash par USB sont les
  mêmes partout. La carte n°2 se reflashe une dernière fois avec `firmware/node`.
- N'importe quelle carte nœud dépanne le dongle : on la débranche du secteur, on la
  branche en USB au Pi, et elle prend le relais. Sa portée est plus faible que celle de
  la XIAO (antenne du module seule).
- Un nœud branché en USB à un poste qui fait tourner `dmxnowd` devient son dongle : pour
  un flash ou un test par l'USB (DMX par l'USB, par exemple), arrêter le démon avant.
- Le firmware du nœud grossit d'environ 7 ko de flash et 14 ko de RAM (application du
  dongle incluse).
