# Mise en service

Prérequis : nœuds flashés ([flash.md](flash.md)), montés et câblés
([assemblage.md](assemblage.md), [cablage.md](cablage.md)), **liste de contrôle de
[securite.md §4](securite.md) cochée** 🔴 ; dongle flashé.

## 1. Raspberry Pi

Raspberry Pi OS **Bookworm** (Python ≥ 3.11), QLC+ installé.

1. Brancher le dongle sur un port USB du Pi (rallonge conseillée), antenne verticale.
2. Installer le démon :
   ```
   git clone … && cd dmxnow/pi
   sudo ./install.sh
   sudo usermod -a -G dmxnow $USER      # CLI sans sudo, après reconnexion
   ```
   L'installeur tire un `net_id` aléatoire, génère la clé réseau `/etc/dmxnow/net_key`,
   crée `/dev/dmx-dongle` d'après le numéro de série du dongle et démarre `dmxnowd`.
   Si le dongle n'était pas branché : le brancher et relancer `sudo ./install.sh`.
3. Régler `/etc/dmxnow/dmxnowd.toml` ([exemple](../pi/dmxnowd.toml.example)) :
   - `universes` : univers Art-Net à transmettre (4 au plus par dongle) ;
   - `channel` : canal radio, **1, 6 ou 11**, le moins encombré par le Wi-Fi du lieu ;
   - `power_dbm = 15` : **ne pas augmenter** (≈ 20 dBm PIRE avec l'antenne 5 dBi, limite
     européenne).

   Puis `sudo systemctl restart dmxnowd`.
4. Vérifier : `dmxnow status` doit indiquer le dongle connecté, le canal et le `net_id`.

## 2. QLC+

Entrées/Sorties → pour chaque univers utilisé : sortie **Art-Net**, interface
`127.0.0.1`, univers Art-Net = une des valeurs de `universes`. Mode de transmission
« Complète » recommandé [V-FW-08]. Un seul logiciel doit émettre de l'Art-Net vers ces
univers.

## 3. Enrôler chaque nœud

Un nœud neuf (`net_id` 0) n'écoute encore aucun réseau : il accepte seulement les
commandes de configuration. Mettre les nœuds sous tension un par un
(**après la liste de contrôle**).

1. Lister :
   ```
   dmxnow nodes
   ```
   Le nœud apparaît sous son nom `node-XXXXXX` avec `NOT ENROLLED`. Vérifier la
   **variante** (rubans / projecteur seul) et le **RSSI** (au-dessus de −75 dBm
   conseillé [À valider : seuil à confirmer par les essais de portée]).
2. L'identifier si plusieurs nœuds sont neufs : `dmxnow identify node-XXXXXX` (les
   rubans clignotent ; la LED D4 si montée).
3. Enrôler :
   ```
   dmxnow enroll node-3A4F21 --universe 0 --address 1 --name lyre-cour --slots 40
   ```
   - `--universe` / `--address` : univers et **adresse de départ du nœud** (canal du
     relais, puis rubans, [cablage.md §5](cablage.md)) ;
   - `--name` : 16 caractères au plus, sert ensuite dans toutes les commandes et au nom du
     point d'accès de maintenance ;
   - `--slots` : **dernier canal DMX utilisé par le projecteur** : des trames plus
     courtes réduisent la latence (arbitrage A3). Par défaut 512 (compatibilité maximale,
     `dmxnow nodes` le signale).

   L'enrôlement transmet aussi la **clé réseau** : dès lors, le nœud refuse toute
   commande non signée par ce Pi (sauf `IDENTIFY`).
4. Définir le **mot de passe de maintenance** (8 à 32 caractères), à conserver avec la
   documentation de l'installation :
   ```
   dmxnow set lyre-cour maint_password=choisir-un-mot-de-passe
   ```
   Il n'est pas relisible par la CLI (seule la console USB J3 l'affiche, hors secteur).
5. Régler le projecteur sur son adresse DMX propre (après les canaux du nœud), puis
   vérifier dans QLC+ : relais (canal `start_address` ≥ 128 = allumé), projecteur,
   rubans.

Autres réglages (`dmxnow set <nœud> clé=valeur`, liste dans
[PROTOCOL §6.4](../spec/PROTOCOL.md)) :

| Clé | Défaut | Effet |
|-----|--------|-------|
| `relay_dmx` | 1 | 1 = le relais suit le canal `start_address` ; 0 = commande seule |
| `relay_power_on` | 2 | État du relais à la mise sous tension : 0 éteint, 1 allumé, 2 dernier état |
| `relay_min_interval_ms` | 3000 | Intervalle minimal entre deux commutations (protège le relais et les alimentations) |
| `loss_blackout_ms` | 0 | 0 = garder la dernière trame si le flux s'arrête ; sinon noir après ce délai |
| `pwm_mode` | 0 | Rubans : 0 = 8 bits (4 canaux), 1 = 16 bits (8 canaux) |
| `gamma_x10` | 22 | Gamma des rubans × 10 |
| `fade_on_ms` | 500 | Fondu des rubans à l'allumage |
| `status_led` | 0 | 1 si la LED D4 est montée |
| `powercycle_maint` | 1 | 1 = trois mises sous tension rapprochées ouvrent la maintenance |

## 4. Commandes courantes

| Besoin | Commande |
|--------|----------|
| État des nœuds | `dmxnow nodes` (`SILENT` = plus de heartbeat) |
| État du démon et du dongle | `dmxnow status` |
| Forcer le relais / le rendre au DMX | `dmxnow relay lyre-cour on\|off\|auto` |
| Faire clignoter | `dmxnow identify lyre-cour -d 10` (`all` = tous) |
| Lire la configuration | `dmxnow get lyre-cour` |
| Redémarrer | `dmxnow reboot lyre-cour` |
| Remise à zéro usine | `dmxnow factory-reset lyre-cour --yes` (il faudra le réenrôler) |

Référence complète : [pi/README.md](../pi/README.md).

## 5. Maintenance d'un nœud (page web, OTA)

Trois façons d'ouvrir la maintenance :
- `dmxnow maintenance lyre-cour [-t 600]` ;
- appui **≥ 3 s** sur le poussoir SW1 (à travers le couvercle basse tension) ;
- **trois mises sous tension** à moins de 5 s d'écart (si `powercycle_maint` = 1).

Puis : réseau Wi-Fi `dmxnow-<nom>`, mot de passe de maintenance, http://192.168.4.1/.
La page montre l'état et permet de régler nom, univers, adresse, trame DMX, relais,
canal radio, `net_id`, de forcer le relais et de téléverser un firmware
([flash.md §4](flash.md)). Le DMX continue d'être rendu pendant la maintenance
[V-FW-05]. Sortie : bouton « Quitter la maintenance », nouvel appui de 3 s, ou délai.

**Remise à zéro usine sans Pi** : SW1 maintenu **≥ 10 s** ; efface configuration, clé
réseau et mot de passe (un nouveau mot de passe aléatoire est tiré).

## 6. Changer de canal radio

1. `dmxnow set all radio_channel=11` (chaque nœud change 500 ms après son accusé) ;
2. `channel = 11` dans `/etc/dmxnow/dmxnowd.toml`, puis `sudo systemctl restart dmxnowd`.

Un nœud éteint pendant l'opération retrouve seul le réseau par balayage des canaux au
bout de 60 s sans réseau (A5).

## 7. LED d'état (option D4)

| LED | État |
|-----|------|
| Fixe | Flux DMX reçu |
| Clignotement lent (1 Hz) | Réseau (dongle) entendu, pas de flux DMX |
| Double éclat | Aucun dongle entendu |
| Clignotement rapide (5 Hz) | Maintenance |
| Clignotement 1 Hz avec les rubans | `IDENTIFY` |

## 8. Dépannage

| Symptôme | Causes probables | Vérifier |
|----------|------------------|----------|
| `dmxnow status` : dongle absent | Dongle débranché, règle udev manquante, port pris par un autre programme | `ls -l /dev/dmx-dongle`, relancer `sudo ./install.sh`, `journalctl -u dmxnowd` |
| Nœud absent de `dmxnow nodes` | Pas de secteur, F1 fondu 🔴, mauvais canal, trop loin | Attendre 60 s (balayage) ; rapprocher le dongle ; ne jamais remplacer F1 sans chercher la cause ([securite.md §5](securite.md)) |
| `SILENT` | Nœud éteint ou hors de portée | RSSI précédent, obstacles métalliques, antenne du dongle verticale |
| `NOT ENROLLED` après enrôlement | Remise à zéro (SW1 10 s) ou commande perdue | Relancer `dmxnow enroll` |
| `AUTH_FAILED` | Nœud enrôlé par un autre Pi ou clé réinstallée | `factory-reset` par SW1 (10 s), puis réenrôler |
| Projecteur sans réaction, relais OK | Adresse du projecteur, câble ou fiche XLR, terminaison 120 Ω, `--slots` trop petit | Adresse ≤ `dmx_out_slots` ; brochage XLR ([cablage.md §3](cablage.md)) |
| Relais ne suit pas le DMX | `relay_dmx` = 0, relais forcé (`*` dans `dmxnow nodes`), intervalle minimal | `dmxnow relay <nœud> auto` |
| Rubans éteints | Carte cassée (variante), polarité de J5, F2, alimentation LED sur J7 éteinte avec le relais | Variante dans `dmxnow nodes` ; J5 au multimètre (hors secteur) |
| Scintillement, pertes (`lost` croissant) | Wi-Fi sur le même canal, portée | Changer de canal (§6) |
| Mise à jour OTA annulée | Aucun paquet radio dans les 60 s après le redémarrage | Refaire l'OTA à portée du dongle, démon en marche |
