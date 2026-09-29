# ADR 0001 : Transport radio ESP-NOW

**Statut :** Accepté (cahier des charges, décision 1)

## Contexte

Il faut transporter un univers DMX (512 octets) à 44 Hz vers des dizaines de nœuds, avec une latence de quelques ms, sans infrastructure.

## Décision

ESP-NOW en broadcast sur un canal Wi-Fi fixe configurable. Le Wi-Fi associé (Art-Net) n'est utilisé qu'en maintenance.

## Conséquences

- Pas de point d'accès ni d'association : démarrage immédiat, aucune dépendance au réseau du lieu.
- Broadcast : un seul envoi pour tous les nœuds d'un univers ; coût radio indépendant du nombre de nœuds.
- Pas d'acquittement en broadcast : la répétition continue tient lieu de fiabilité (PROTOCOL §4.4, SPEC §5.3).
- Le broadcast ESP-NOW ne peut pas être chiffré (voir ADR 0015).

## Alternatives écartées

- Wi-Fi + Art-Net en exploitation : dépend d'un point d'accès, latences variables (économie d'énergie, multicast/broadcast Wi-Fi émis au débit de base).
- Zigbee, Thread, BLE : débit insuffisant pour 512 octets à 44 Hz avec marge.
- LoRa : débit de quelques kbit/s.
- CPL : latence irrégulière, perturbé par les alimentations à découpage des projecteurs.
