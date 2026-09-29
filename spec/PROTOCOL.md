# dmxnow : Spécification du protocole

Version du protocole : **1** (validé le 2026-09-25)
Documents liés : [SPEC.md](SPEC.md), [ADR 0001](adr/0001-transport-esp-now.md),
[ADR 0011](adr/0011-esp-now-v2-trame-unique.md), [ADR 0012](adr/0012-liaison-serie-cobs.md),
[ADR 0013](adr/0013-commandes-broadcast-ack.md), [ADR 0015](adr/0015-authentification-commandes.md).

Conventions :
- Tous les entiers multi-octets sont en **petit-boutiste** (little-endian), structures
  empaquetées sans alignement.
- « Octet » = 8 bits. Les offsets sont en octets depuis le début de la structure.
- Les mots DOIT, NE DOIT PAS, DEVRAIT, PEUT ont le sens de la RFC 2119.
- Les arbitrages sont listés dans SPEC.md §9.

---

## 1. Vue d'ensemble

![Vue d'ensemble : QLC+, démon, dongle, nœuds](../docs/diagrams/vue-ensemble.png)

Deux liaisons sont spécifiées :
1. **Liaison radio** dongle ↔ nœuds (ESP-NOW), §2 à §7.
2. **Liaison série** démon Pi ↔ dongle (USB CDC), §8.

Les deux partagent le même CRC (§2.4) et le même encodage des commandes, de sorte que
le Pi et les firmwares utilisent le même code de sérialisation (`firmware/common`
porté à l'identique en Python dans `pi/`, avec vecteurs de test communs).

---

## 2. Couche radio ESP-NOW

### 2.1 Version d'ESP-NOW : v2, trame unique par univers

**Choix : ESP-NOW v2 (charge utile jusqu'à 1470 octets), un univers complet par paquet.
Mode de repli « fragmenté v1 » (paquets ≤ 250 octets) spécifié et implémenté, sélectionnable
par configuration du dongle.**

Justification (détails et calculs dans SPEC.md §5) :
- ESP-NOW v2 est disponible à partir d'**ESP-IDF v5.4** (constante
  `ESP_NOW_MAX_DATA_LEN_V2` = 1470 ; v5.4 et v5.4.1 utilisaient 1490, corrigé à
  1470 à partir de v5.4.2). Source : ESP-IDF Programming Guide, section ESP-NOW,
  et ESP-FAQ ESP-NOW (docs.espressif.com).
- Le framework Arduino-ESP32 **3.2 et suivants** repose sur ESP-IDF ≥ 5.4
  (3.3.x ↔ IDF 5.5). La plateforme PlatformIO officielle `espressif32` ne suit
  pas Arduino 3.x ; la plateforme communautaire **pioarduino**
  (`github.com/pioarduino/platform-espressif32`) le fait (Arduino 3.3.12 / IDF 5.5.5
  au moment de la rédaction). Voir ADR 0011 et SPEC « À valider » V-FW-01.
- Un univers de 512 canaux + en-tête (18 octets) = 530 octets tient dans **un seul**
  paquet : une trame perdue = un rafraîchissement perdu, jamais un univers partiellement
  mis à jour (pas de « déchirure » entre fragments), temps d'antenne réduit
  (~0,9 ms contre ~1,6 ms en 3 fragments à 6 Mbit/s), probabilité de perte divisée
  par ~3, pas de réassemblage à l'exécution.
- Le mode fragmenté reste utile si un nœud est bloqué sur un firmware v1 ou si le
  framework doit être rétrogradé ; il est défini §4.2.

### 2.2 Paramètres radio

| Paramètre            | Valeur par défaut | Plage / options                                  | Porté par        |
|----------------------|-------------------|--------------------------------------------------|------------------|
| Canal Wi-Fi          | 6                 | 1 à 13 (recommandé : 1, 6 ou 11)                 | dongle et nœuds  |
| Mode Wi-Fi           | STA non associé, économie d'énergie désactivée (`WIFI_PS_NONE`) | - | tous |
| Débit PHY d'émission | 802.11g 6 Mbit/s (OFDM) | 1, 2, 5,5, 11 Mbit/s (DSSS) ; 6, 12, 24 Mbit/s (OFDM) | émetteur (dongle ; nœuds pour HEARTBEAT/ACK) |
| Puissance d'émission | 15 dBm            | 2 à 20 dBm                                       | dongle et nœuds  |
| Adresse DMX_DATA, COMMAND, BEACON | broadcast `FF:FF:FF:FF:FF:FF` | - | dongle |
| Adresse HEARTBEAT, ACK | MAC du dongle (unicast) | broadcast tant que le dongle est inconnu | nœuds |
| Chiffrement ESP-NOW  | aucun (le broadcast ne peut pas être chiffré par ESP-NOW) | - | - |

Remarques :
- Le débit se règle par pair avec `esp_now_set_peer_rate_config()` (IDF ≥ 5.x), y
  compris pour le pair broadcast. Disponibilité exacte dans Arduino 3.x : à valider
  (V-FW-02).
- 6 Mbit/s OFDM est un compromis : ~5× moins de temps d'antenne que 1 Mbit/s DSSS, au
  prix d'environ 6 à 8 dB de sensibilité. Sur des distances de scène (< 30 m, vue
  directe), la marge est suffisante ; en cas de difficulté, passer à 1 ou 2 Mbit/s
  (le récepteur accepte n'importe quel débit, aucun changement côté nœud).

### 2.3 En-tête commun (18 octets)

Tout paquet radio commence par cet en-tête, suivi de `length` octets de charge utile,
puis éventuellement d'une remorque d'authentification (§7).

| Offset | Taille | Champ       | Description |
|-------:|-------:|-------------|-------------|
| 0      | 2      | `magic`     | `0x4E44` (octets `'D'`,`'N'` sur le fil : `0x44 0x4E`). Rejette tout trafic ESP-NOW d'un autre protocole. |
| 2      | 1      | `version`   | Version du protocole, **1**. Un récepteur DOIT rejeter une version différente (compteur `rejected`). |
| 3      | 1      | `type`      | Type de message (§3). |
| 4      | 2      | `net_id`    | Identifiant de réseau, 1 à 65535 (0 réservé = « non configuré »). Un nœud DOIT ignorer tout paquet d'un autre `net_id`. |
| 6      | 2      | `universe`  | Port-Address Art-Net 15 bits (0 à 32767). `0xFFFF` = sans objet. |
| 8      | 2      | `seq`       | Numéro de séquence (sens selon le type). |
| 10     | 2      | `offset`    | Décalage de la charge utile dans l'objet transporté (index de canal DMX 0-based pour DMX_DATA, 0 sinon). |
| 12     | 2      | `length`    | Longueur de la charge utile en octets (hors en-tête et hors remorque). |
| 14     | 1      | `flags`     | bit 0 `LAST` (dernier fragment), bit 1 `FRAG` (paquet fragmenté), bit 2 `AUTH` (remorque d'authentification présente), bits 3 à 7 réservés à 0. |
| 15     | 1      | `reserved`  | 0 à l'émission, ignoré à la réception. |
| 16     | 2      | `crc16`     | CRC-16 (§2.4) sur les octets 0 à 15 de l'en-tête puis la charge utile **et** la remorque éventuelle. |

Taille totale du paquet = 18 + `length` + (12 si `AUTH`).

### 2.4 CRC

**CRC-16/CCITT-FALSE** : polynôme `0x1021`, valeur initiale `0xFFFF`, pas de
réflexion, pas de XOR final. Valeur de contrôle sur l'ASCII `"123456789"` : `0x29B1`.

Le CRC est calculé sur l'en-tête **sans** le champ `crc16` (octets 0 à 15), puis sur
tout ce qui suit l'en-tête. Remarque honnête : la couche MAC 802.11 protège déjà chaque
trame par un FCS CRC-32 et le matériel jette les trames corrompues. Le CRC16 applicatif
ne sert donc pas contre les erreurs radio, mais : (a) il détecte les erreurs de
sérialisation, de copie mémoire et de version entre firmwares ; (b) il est identique sur
la liaison série où il est indispensable ; (c) son coût est négligeable (~2 µs sur 530
octets par table de 256 entrées).

### 2.5 Validation à la réception (ordre imposé)

Un récepteur DOIT rejeter silencieusement (en incrémentant `rejected_frames`) tout
paquet qui ne satisfait pas, dans cet ordre :
1. taille reçue ≥ 18 ;
2. `magic` correct ;
3. `version` = 1 ;
4. `net_id` = `net_id` configuré (sauf nœud non configuré, `net_id` = 0, qui accepte
   COMMAND et BEACON de tout réseau pour l'enrôlement, jamais DMX_DATA) ;
5. taille reçue = 18 + `length` + (12 si `AUTH`) ;
6. CRC correct ;
7. `type` connu ;
8. contrôles propres au type (§4 à §6) ;
9. authentification si requise (§7).

Le traitement dans le callback de réception ESP-NOW DOIT se limiter à ces contrôles et à
une copie en mémoire tampon (le callback s'exécute dans la tâche Wi-Fi).

---

## 3. Types de messages

| Code   | Nom          | Sens              | Adressage  | Périodicité |
|--------|--------------|-------------------|------------|-------------|
| `0x01` | `DMX_DATA`   | dongle → nœuds    | broadcast  | ≥ 44 Hz par univers actif |
| `0x02` | *réservé* `DMX_SYNC` | - | - | non utilisé en v1 |
| `0x10` | `COMMAND`    | dongle → nœud(s)  | broadcast, cible dans la charge utile | à la demande, répétée (§6) |
| `0x11` | `ACK`        | nœud → dongle     | unicast    | en réponse à COMMAND |
| `0x20` | `HEARTBEAT`  | nœud → dongle     | unicast (broadcast si dongle inconnu) | 2 s ± 250 ms |
| `0x30` | `BEACON`     | dongle → nœuds    | broadcast  | 1 Hz |

---

## 4. DMX_DATA (`0x01`)

- `universe` : Port-Address de l'univers.
- `seq` : compteur d'émission **par univers**, incrémenté (modulo 65536) à chaque
  émission, y compris les répétitions de données inchangées. Sert au comptage des pertes.
- `offset` : index 0-based du premier canal transporté (canal DMX 1 = index 0).
- `length` : nombre de canaux transportés (1 à 512 ; `offset + length` ≤ 512).
- Charge utile : valeurs des canaux. Le code de départ DMX est implicitement `0x00`
  (codes de départ alternatifs hors périmètre).

Sémantique : les canaux au-delà de `offset + length` du dernier paquet reçu valent 0
(même comportement qu'une trame Art-Net courte).

### 4.1 Mode v2 (défaut)

Un paquet par univers et par émission : `offset` = 0, `length` = nombre de canaux reçus
d'Art-Net (pair, 2 à 512), `flags` = `LAST`. Taille maximale 530 octets.

### 4.2 Mode fragmenté v1 (repli)

Charge utile maximale par paquet : 250 − 18 = 232 octets. Un univers de 512 canaux est
envoyé en 3 paquets de même `seq` : offsets 0 (232), 232 (232), 464 (48). `flags` =
`FRAG` sur tous, plus `LAST` sur le dernier. Les fragments sont émis dos à dos.

Réassemblage côté nœud :
- tampon de réassemblage par univers suivi (un seul univers par nœud), indexé par `seq` ;
- un fragment dont `seq` diffère du réassemblage en cours démarre un nouveau
  réassemblage ; le réassemblage précédent incomplet est **fusionné** dans la trame
  courante (les fragments reçus s'appliquent, les autres canaux gardent leur valeur
  précédente) ;
- la trame est validée à réception du fragment `LAST` si tous les fragments attendus
  (déduits de `offset + length` du `LAST`) sont présents, sinon fusion partielle comme
  ci-dessus ;
- un nœud v2 accepte indifféremment les deux modes.

### 4.3 Comptage des pertes

Pour son univers, le nœud calcule `gap = (seq − last_seq − 1) mod 65536`. Si
`gap < 1000`, `lost_frames += gap` ; sinon (redémarrage du dongle) le compteur n'est
pas modifié et `last_seq` est réinitialisé. `rx_frames` compte les trames valides.

### 4.4 Cadence (règle « émission sur événement + rafraîchissement minimal »)

Appliquée à l'identique par le dongle (vers la radio) et par le nœud (vers la ligne DMX) :
- à l'arrivée de données nouvelles, émission **immédiate** (sous réserve d'un intervalle
  minimal de 10 ms par univers ; les données arrivées pendant ce délai sont fusionnées et
  émises à son échéance) ;
- en l'absence de données nouvelles, ré-émission de la dernière trame toutes les
  1/44 s (22,7 ms) ;
- le dongle cesse d'émettre un univers après `hold_timeout` (défaut 10 s) sans données
  du Pi pour cet univers.

---

## 5. HEARTBEAT (`0x20`) et BEACON (`0x30`)

### 5.1 HEARTBEAT

En-tête : `universe` = univers du nœud, `seq` = compteur de heartbeats, `offset` = 0.
Émis toutes les 2 s avec une gigue aléatoire uniforme de ± 250 ms (évite la
synchronisation de dizaines de nœuds), ainsi qu'immédiatement après le démarrage, un
changement de configuration, un changement d'état du relais et l'entrée en maintenance.

Charge utile (56 octets) :

| Offset | Taille | Champ               | Description |
|-------:|-------:|---------------------|-------------|
| 0      | 6      | `mac`               | MAC STA du nœud (redondant avec l'adresse source, utile pour le Pi) |
| 6      | 16     | `name`              | Nom UTF-8, complété par des `0x00` |
| 22     | 2      | `start_address`     | Adresse DMX de départ (1 à 512) |
| 24     | 3      | `fw_version`        | majeur, mineur, correctif |
| 27     | 1      | `variant`           | 1 = projecteur seul (carte cassée), 2 = projecteur + rubans (carte entière) |
| 28     | 1      | `relay`             | bit 0 état réel du contact, bit 1 forçage par commande actif, bit 2 commutation différée en attente (anti-rebond) |
| 29     | 4      | `relay_switch_count`| Nombre total de commutations (persistant) |
| 33     | 1      | `rssi`              | int8, dBm, moyenne glissante (α = 1/8) des DMX_DATA reçus |
| 34     | 4      | `rx_frames`         | Trames DMX_DATA valides de son univers depuis le démarrage |
| 38     | 4      | `lost_frames`       | Trames perdues (§4.3) |
| 42     | 4      | `rejected_frames`   | Paquets rejetés (§2.5) |
| 46     | 4      | `uptime_s`          | Secondes depuis le démarrage |
| 50     | 1      | `status`            | bit 0 flux DMX présent, bit 1 blackout sur perte actif, bit 2 maintenance, bit 3 identification en cours, bit 4 dongle connu |
| 51     | 1      | `radio_channel`     | Canal Wi-Fi courant |
| 52     | 2      | `dmx_out_slots`     | Longueur de la trame DMX émise |
| 54     | 1      | `reset_reason`      | Valeur `esp_reset_reason_t` |
| 55     | 1      | `reserved`          | 0 |

Taille paquet : 74 octets.

### 5.2 BEACON

Émis en broadcast par le dongle à 1 Hz, **même sans univers actif**. Permet à un nœud
d'apprendre l'adresse MAC du dongle et de savoir que le réseau est présent quand QLC+ est
arrêté. `universe` = `0xFFFF`, `seq` = compteur. Charge utile (8 octets) :
`fw_version` (3), `active_universes` (1), `uptime_s` (4).

### 5.3 Apprentissage de l'adresse du dongle

Un nœud apprend la MAC du dongle comme adresse source du premier paquet valide
(DMX_DATA, COMMAND ou BEACON) de son `net_id`, l'ajoute comme pair ESP-NOW et lui
adresse ensuite HEARTBEAT et ACK en unicast (acquittement et retransmissions MAC
matériels). Si aucun paquet du dongle n'est reçu pendant 30 s, l'adresse est oubliée et
les HEARTBEAT repassent en broadcast. Un seul dongle par `net_id` est supporté (plusieurs
dongles sur un même réseau : hors périmètre v1).

---

## 6. COMMAND (`0x10`) et ACK (`0x11`)

### 6.1 COMMAND

En-tête : `universe` = `0xFFFF`, `seq` = `cmd_id` (attribué par le démon Pi, croissant
modulo 65536), `offset` = 0, `flags` bit `AUTH` selon §7.

Charge utile :

| Offset | Taille | Champ     | Description |
|-------:|-------:|-----------|-------------|
| 0      | 6      | `target`  | MAC du nœud visé, ou `FF:FF:FF:FF:FF:FF` = tous les nœuds du réseau |
| 6      | 1      | `opcode`  | §6.3 |
| 7      | n      | `args`    | Arguments selon l'opcode |

Un nœud dont la MAC ne correspond pas (et qui n'est pas visé par broadcast) ignore la
commande sans l'acquitter.

### 6.2 Fiabilité des commandes

Les commandes ne sont pas périodiques ; la répétition à 44 Hz ne les protège pas.
Mécanisme retenu (ADR 0013) :
- **Commande ciblée** : le dongle émet, attend un ACK 30 ms, ré-émet jusqu'à
  5 tentatives au total avec délais 30, 60, 120, 240 ms (total < 0,5 s). Sans ACK, il
  renvoie `CMD_RESULT = TIMEOUT` au Pi.
- **Commande broadcast** (tous les nœuds) : 3 émissions espacées de 20 ms, sans
  attente d'ACK ; les ACK reçus pendant 1 s sont remontés au Pi, qui en déduit les nœuds
  n'ayant pas répondu (il connaît la liste par les heartbeats) et peut les relancer en
  commande ciblée.
- **Idempotence** : le nœud mémorise les 16 derniers `cmd_id` traités (avec leur
  statut). Un doublon n'est **pas** ré-exécuté ; l'ACK mémorisé est renvoyé.
- L'ACK est envoyé en unicast (retransmissions MAC matérielles en plus).
- Une commande dont l'effet est différé (relais soumis à l'anti-rebond, changement de
  canal radio) est acquittée immédiatement avec le statut `OK` ; l'effet réel est
  visible dans le heartbeat suivant (émis dès l'application).

### 6.3 Opcodes

| Code   | Nom             | Arguments | Effet |
|--------|-----------------|-----------|-------|
| `0x01` | `IDENTIFY`      | `duration_s` u16 (0 = arrêt) | Fait clignoter le nœud à 1 Hz : sorties PWM (si rubans) à 100 %/0 %, et le canal DMX `identify_slot` (s'il est configuré) à 255/0 en écrasant la valeur reçue. Défaut 10 s. |
| `0x02` | `SET_CONFIG`    | liste TLV (§6.4) | Applique et persiste la configuration de façon atomique (tout ou rien). |
| `0x03` | `GET_CONFIG`    | - | L'ACK contient la configuration complète en TLV (secrets exclus). |
| `0x04` | `RELAY`         | `mode` u8 : 0 = forcer éteint, 1 = forcer allumé, 2 = automatique (suivre le canal DMX) | Voir SPEC §4.5 (priorités). Soumis à l'intervalle minimal entre commutations. |
| `0x05` | `MAINTENANCE`   | `timeout_s` u16 (0 = défaut 600) | Passe en mode maintenance (§SPEC 4.9). |
| `0x06` | `REBOOT`        | - | Redémarre après envoi de l'ACK (délai 600 ms, au-delà de la dernière retransmission du dongle à 450 ms : une répétition est servie par l'historique et non exécutée deux fois ; porté de 200 à 600 ms le 2026-09-28). |
| `0x07` | `FACTORY_RESET` | `confirm` u32 = `0x52455345` (« RESE ») | Efface la configuration NVS (conserve `relay_switch_count`), redémarre. Aussi déclenchable localement par un appui ≥ 10 s sur SW1 (SPEC §4.9). |

### 6.4 Clés de configuration (TLV)

Chaque élément : `key` u8, `len` u8, `value` (`len` octets). Clé inconnue ⇒ statut
`INVALID_ARG` et rien n'est appliqué.

| Clé    | Nom                    | Type  | Défaut        | Contraintes / remarques |
|--------|------------------------|-------|---------------|-------------------------|
| `0x01` | `universe`             | u16   | 0             | 0 à 32767 |
| `0x02` | `start_address`        | u16   | 1             | 1 à 512 − empreinte + 1 |
| `0x03` | `name`                 | 1 à 16 octets UTF-8 | `node-XXXXXX` (3 derniers octets MAC) | |
| `0x04` | `radio_channel`        | u8    | 6             | 1 à 13 ; appliqué 500 ms après l'ACK |
| `0x05` | `relay_dmx`            | u8    | 1             | 1 = le canal `start_address` pilote le relais ; 0 = relais piloté uniquement par commande et état au démarrage |
| `0x06` | `relay_power_on`       | u8    | 2             | 0 = éteint, 1 = allumé, 2 = dernier état |
| `0x07` | `relay_min_interval_ms`| u16   | 3000          | 1000 à 60000 |
| `0x08` | `loss_blackout_ms`     | u32   | 0             | 0 = conserver la dernière trame indéfiniment ; sinon délai avant blackout (DMX à 0, PWM à 0 ; le relais n'est **pas** affecté) |
| `0x09` | `pwm_mode`             | u8    | 0             | 0 = 4 canaux 8 bits, 1 = 4 canaux 16 bits (MSB puis LSB) |
| `0x0A` | `gamma_x10`            | u8    | 22            | 10 (linéaire) à 30 |
| `0x0B` | `fade_on_ms`           | u16   | 500           | 0 à 10000 |
| `0x0C` | `pwm_freq_hz`          | u16   | 4882          | 1000 à 19531 ; la résolution est déduite (§SPEC 4.7) |
| `0x0D` | `dmx_out_slots`        | u16   | 512           | 24 à 512 ; à régler à l'adresse de fin du projecteur (arbitrage A3) |
| `0x0E` | `identify_slot`        | u16   | 0             | 0 = aucun ; sinon canal DMX forcé 255/0 pendant IDENTIFY |
| `0x0F` | `net_id`               | u16   | 0 (non configuré) | 1 à 65535 |
| `0x10` | `maint_password`       | 8 à 32 octets | aléatoire, cf. SPEC 4.9 | écriture seule |
| `0x11` | `net_key`              | 32 octets | absent | écriture seule (§7) |
| `0x12` | `powercycle_maint`     | u8    | 1             | 1 = 3 mises sous tension rapprochées (< 5 s) ⇒ maintenance ; 0 = désactivé (SPEC §4.9, A6) |
| `0x13` | `status_led`           | u8    | 0             | 1 = LED d'état D4 montée et pilotée (SPEC §4.9, A7) |

Empreinte DMX du nœud à partir de `start_address` : canal relais (si `relay_dmx` = 1),
puis PWM1..PWM4 (8 bits) ou PWM1 MSB, PWM1 LSB, … PWM4 LSB (16 bits) si la variante
rubans est détectée. Empreinte : 1, 5 ou 9 canaux. Si `relay_dmx` = 0, les canaux PWM
commencent à `start_address`.

### 6.5 ACK

En-tête : `universe` = `0xFFFF`, `seq` = `cmd_id` acquitté.

| Offset | Taille | Champ    | Description |
|-------:|-------:|----------|-------------|
| 0      | 1      | `opcode` | Opcode acquitté |
| 1      | 1      | `status` | 0 `OK`, 1 `UNKNOWN_OPCODE`, 2 `INVALID_ARG`, 3 `AUTH_FAILED`, 4 `UNSUPPORTED` (ex. PWM sur variante projecteur seul), 5 `INTERNAL_ERROR` |
| 2      | n      | `data`   | `GET_CONFIG` : TLV ; `RELAY` : `relay` (même codage que HEARTBEAT) ; sinon vide |

---

## 7. Authentification des commandes (arbitrage A4, retenu)

Menace visée : un tiers (ou une autre installation dmxnow mal configurée) qui enverrait
`MAINTENANCE` (ouvre un point d'accès et l'OTA), `FACTORY_RESET` ou `RELAY`. Le `net_id`
n'est **pas** une protection : il est lisible en clair.

- Clé `net_key` de 32 octets, partagée par le Pi et les nœuds d'un réseau, fixée par
  `SET_CONFIG` (clé `0x11`). Le dongle ne la connaît pas : le Pi calcule la remorque.
- Remorque de 12 octets ajoutée après la charge utile, `flags.AUTH` = 1 :
  `counter` u32 puis `mac8` = 8 premiers octets de
  `HMAC-SHA256(net_key, en-tête[0..15] ‖ charge utile ‖ counter)`.
- `counter` strictement croissant (persisté par le démon Pi). Le nœud rejette tout
  `counter` ≤ au dernier accepté (anti-rejeu), persiste le dernier accepté en NVS
  (commandes rares : usure négligeable).
- Un nœud **sans** `net_key` accepte les commandes non authentifiées (enrôlement initial,
  confiance au premier usage). Dès qu'une clé est définie, toute COMMAND sans remorque
  valide reçoit `AUTH_FAILED` (sauf `IDENTIFY`, inoffensif).
- DMX_DATA, BEACON, HEARTBEAT et ACK ne sont pas authentifiés (choix explicite : la
  menace retenue est l'interférence accidentelle, pas le détournement délibéré d'un
  spectacle ; voir risque R-11).

---

## 8. Liaison série Pi ↔ dongle

### 8.1 Couche physique

USB « Serial/JTAG » intégré de l'ESP32-C3 (classe CDC-ACM), vitesse déclarée ignorée
(le démon ouvre le port à 921600 bauds par convention). Nom stable côté Pi :
`/dev/dmx-dongle` via règle udev (VID:PID `303a:1001` + numéro de série, SPEC 4.11).

### 8.2 Encadrement

Trame logique : `type` u8, `seq` u8, `payload` (0 à 1020 octets), `crc16` u16
(CRC §2.4 sur `type`, `seq` et `payload`).

La trame logique est encodée en **COBS** puis terminée par un octet `0x00`. Justification
(ADR 0012) : surcoût borné (1 octet pour 254, soit ≤ 3 octets pour un univers) contre un
doublement possible en SLIP ; resynchronisation immédiate sur le prochain `0x00` après une
erreur ou une connexion en cours de flux. Toute trame dont le décodage COBS échoue, dont
la longueur est < 4 ou dont le CRC est faux est jetée (compteur `serial_errors`).

`seq` : compteur par émetteur (modulo 256), sert au diagnostic des pertes série.

### 8.3 Messages Pi → dongle

| Type   | Nom             | Charge utile |
|--------|-----------------|--------------|
| `0x01` | `UNIVERSE`      | `universe` u16, `length` u16, `data[length]` (2 à 512) |
| `0x02` | `COMMAND`       | `cmd_id` u16, `flags` u8 (bit 2 = AUTH), `target` 6, `opcode` u8, `args`…, remorque AUTH éventuelle (déjà calculée par le Pi) |
| `0x03` | `DONGLE_CONFIG` | TLV : `0x01` canal u8, `0x02` `net_id` u16, `0x03` débit PHY u8 (énumération `wifi_phy_rate_t`), `0x04` puissance dBm u8, `0x05` `hold_timeout_ms` u32, `0x06` rafraîchissement Hz u8 (défaut 44), `0x07` mode radio u8 (0 = v2, 1 = fragmenté v1). Persisté en NVS du dongle. |
| `0x04` | `PING`          | `token` u32 |
| `0x05` | `GET_STATUS`    | - |

### 8.4 Messages dongle → Pi

| Type   | Nom          | Charge utile |
|--------|--------------|--------------|
| `0x81` | `RADIO_RX`   | `rssi` i8, `src_mac` 6, paquet ESP-NOW brut complet (en-tête inclus). HEARTBEAT et ACK sont ainsi décodés par le Pi avec le même parseur que les firmwares |
| `0x82` | `CMD_RESULT` | `cmd_id` u16, `target` 6, `result` u8 (0 acquitté, 1 expiré sans ACK, 2 broadcast terminé), `attempts` u8 |
| `0x83` | `STATUS`     | `fw_version` 3, `channel` u8, `net_id` u16, `phy_rate` u8, `mode` u8, `active_universes` u8, `tx_ok` u32, `tx_fail` u32, `serial_errors` u32, `coalesced` u32, `uptime_s` u32 |
| `0x84` | `PONG`       | `token` u32 |
| `0x85` | `LOG`        | `level` u8 (0 erreur … 3 debug), texte UTF-8 |

### 8.5 Surveillance de la liaison

- Le démon envoie `PING` chaque seconde ; sans `PONG` pendant 3 s, il ferme et rouvre le
  port (reconnexion USB).
- Le dongle considère le Pi absent après 3 s sans aucune trame valide ; il continue à
  émettre les univers connus jusqu'à `hold_timeout`, puis seulement le BEACON.
- `STATUS` est émis spontanément toutes les 5 s et sur `GET_STATUS`.

### 8.6 Débit

4 univers × 50 Hz (cadence QLC+) × (512 + 9 octets de trame + COBS) ≈ 105 ko/s, bien
en dessous de la capacité pratique de l'USB Serial/JTAG de l'ESP32-C3 (à mesurer :
V-FW-04).

---

## 9. Vecteurs de test

Un fichier `firmware/common/test_vectors.json` (livrable firmware) contiendra, pour
chaque type de message, des paquets de référence encodés (hexadécimal) et leur décodage
attendu, ainsi que des cas invalides (mauvais CRC, mauvaise longueur, `net_id` étranger,
version inconnue). Les tests C++ (`pio test -e native`) et Python (`pytest`) DOIVENT
consommer ce même fichier.

## 10. Évolution du protocole

Toute modification incompatible incrémente `version`. Les champs `reserved` et les bits
de `flags` réservés DOIVENT valoir 0 à l'émission et être ignorés à la réception. Les
charges utiles de HEARTBEAT et STATUS PEUVENT être allongées en fin de structure sans
changer de version (le récepteur lit ce qu'il connaît, `length` fait foi).
