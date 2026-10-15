# ADR 0017 : Mise à jour du firmware par la radio

**Statut :** Accepté (demande de l'utilisateur, 2026-10-15)

## Contexte

Jusqu'ici, un nœud installé se met à jour par sa page de maintenance : `dmxnow
maintenance`, puis un téléphone ou un portable rejoint son point d'accès Wi-Fi et y
téléverse `firmware.bin` (SPEC §4.9). Il faut donc être sur place, à portée Wi-Fi de
chaque nœud. L'utilisateur veut flasher les nœuds à distance, depuis le Pi.

Trois solutions ont été comparées le 2026-10-15 :

| Solution | Pour | Contre |
|----------|------|--------|
| OTA par ESP-NOW, morceaux envoyés par le dongle | Rien de nouveau sur place ; réutilise l'envoi par morceaux des conduites, la signature des commandes et le retour automatique | Lent : quelques minutes par nœud |
| Le nœud rejoint le Wi-Fi du lieu et télécharge sur le Pi | Rapide | Wi-Fi et mot de passe à fournir à chaque nœud ; le nœud quitte la radio ESP-NOW pendant la mise à jour |
| Le Pi rejoint le point d'accès de maintenance du nœud | Simple | Un nœud à la fois, Pi à portée de chaque nœud |

## Décision

- OTA par ESP-NOW : trois opcodes `OTA_BEGIN`, `OTA_WRITE`, `OTA_END` (PROTOCOL §11),
  envoyés nœud par nœud par `dmxnow ota`.
- Morceaux de 192 octets, dans l'ordre. Chaque ACK donne l'offset attendu : un ACK
  perdu ne fait pas écrire deux fois le même morceau, et l'émetteur sait où reprendre.
- Écriture par la bibliothèque `Update`, comme l'OTA web : même slot, même contrôle de
  l'image par ESP-IDF, même confirmation au premier paquet radio valide.
- **Réservé aux nœuds enrôlés avec une clé réseau** : sans clé, les commandes ne sont pas
  authentifiées (PROTOCOL §7) et n'importe qui à portée radio pourrait installer un
  firmware. `OTA_BEGIN` répond alors `AUTH_FAILED` (défaut relevé par la revue de
  sécurité du commit 6ff487e, corrigé le 2026-10-15). Risque restant : un nœud neuf, sans
  clé, accepte l'enrôlement de n'importe qui (choix d'origine, A4), donc aussi d'un
  attaquant qui l'enrôlerait avant le Pi puis le flasherait. Enrôler les nœuds dès leur
  mise en place.
- La CLI refuse avant tout envoi ce qui n'est pas une image d'application, et attend
  la confirmation de la nouvelle image (65 s) avant de passer au nœud suivant.

## Conséquences

- Mise à jour d'un parc entier sans échelle ni déplacement, hors séance.
- La durée dépend de la radio : à mesurer au banc (SPEC V-FW-10).
- Un nœud qui ne reçoit plus le dongle après la mise à jour revient seul à l'ancienne
  image : un firmware cassé côté radio ne peut pas isoler un nœud.
- L'OTA web reste disponible, pour un nœud que la radio n'atteint pas.
