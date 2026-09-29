# Firmware dmxnow

| Dossier | Contenu |
|---------|---------|
| `common/` | Bibliothèque C++17 sans Arduino : protocole v1 (en-tête, validation, CRC16, COBS), configuration TLV, réassemblage, compteur de pertes, logique du relais, gamma, cadence d'émission, HMAC-SHA256 et anti-rejeu, historique des commandes. Tests natifs. |
| `common/test_vectors.json` | Vecteurs communs (PROTOCOL §9), produits par `common/tools/gen_vectors.py` avec une implémentation Python indépendante ; consommés par les tests C++ et, plus tard, par ceux du démon Pi. |
| `node/` | Firmware du nœud, ESP32-C3-MINI-1, Arduino-ESP32 3.3.12 / ESP-IDF 5.5.5 (pioarduino 55.03.312, épinglé). |
| `dongle/` | Firmware du dongle, Seeed XIAO ESP32-C3 sur l'USB du Pi (même plateforme épinglée). |

## Compiler et tester

```
pip install platformio
cd firmware/common && pio test -e native        # 36 tests (nœud + dongle), -Wall -Wextra -Werror
cd firmware/node && pio run -e node             # firmware.bin (OTA) et firmware.factory.bin
cd firmware/dongle && pio run -e dongle         # XIAO ESP32-C3
python3 firmware/common/tools/gen_vectors.py    # après toute évolution du protocole
```

Derrière un proxy TLS d'entreprise, PlatformIO passe son propre bundle `certifi` et
ignore `REQUESTS_CA_BUNDLE` : ajouter le certificat du proxy à ce bundle plutôt que de
désactiver la vérification.

## Flasher un nœud

- Relier un câble USB aux pastilles **J3** : **5V** (pastille 7), GND, D−, D+.
  **Jamais J3-3V3** (sortie du régulateur, courant inverse non garanti) et jamais avec
  le secteur branché (REVIEW 7.6).
- Maintenir SW1 pendant la mise sous tension : chargeur ROM (mode téléchargement).
- `pio run -e node -t upload`, ou `firmware.factory.bin` à l'adresse 0x0 avec esptool.
- Ensuite : mises à jour par OTA depuis la page de maintenance. La nouvelle image est
  **confirmée au premier paquet radio valide** ; sans paquet dans les 60 s, le chargeur
  revient à l'ancienne. Faire les OTA à portée du dongle.

## Mise en service (nœud neuf)

1. Un nœud neuf a `net_id` = 0 : il n'accepte ni DMX ni rien d'autre que des COMMAND et
   des BEACON, de n'importe quel réseau (enrôlement, PROTOCOL §2.5). Son heartbeat part en
   broadcast avec `net_id` 0.
2. Depuis le Pi : `SET_CONFIG` avec `net_id`, `universe`, `start_address`, `name`,
   `dmx_out_slots` (régler à l'adresse de fin du projecteur, arbitrage A3), puis
   `net_key` (A4) : dès lors, toute commande sauf `IDENTIFY` doit être authentifiée.
3. Sans console : page de maintenance (SW1 ≥ 3 s, ou 3 mises sous tension en moins de 5 s
   chacune), point d'accès `dmxnow-<nom>`, mot de passe `maint_password` (aléatoire au
   premier démarrage, affiché sur la console USB J3 au démarrage et à l'entrée en
   maintenance ; à redéfinir de préférence à l'enrôlement :
   `dmxnow set <nœud> maint_password=…`, 8 à 32 caractères), puis http://192.168.4.1/.

## Comportements (où les trouver)

| Fonction | Spécification | Code |
|----------|---------------|------|
| Validation des paquets dans le callback, copie en file | PROTOCOL §2.5 | `node/src/radio.cpp`, `common/src/protocol.cpp` |
| DMX : break 176 µs par inversion de ligne, MAB 12 µs, 250 kbit/s 8N2, `dmx_out_slots` | SPEC 4.4, A3 | `node/src/dmx_out.cpp` |
| Émission sur événement (≥ 10 ms d'écart) + rafraîchissement 44 Hz | PROTOCOL §4.4 | `common/src/dmx.cpp` (`OutputCadence`) |
| Réassemblage v1, fusion partielle | PROTOCOL §4.2 | `common/src/dmx.cpp` (`Reassembler`) |
| Relais : priorités, niveau ≥ 128, anti-rebond différé, NVS seulement à la commutation | SPEC 4.5 | `common/src/relay.cpp`, `node/src/node.cpp` |
| PWM : LEDC 14 bits à 4882 Hz, déphasage d'un quart de période, gamma, fondu | SPEC 4.6-4.7 | `node/src/pwm_out.cpp`, `common/src/gamma.cpp` |
| PWM à 0 avant tout le reste au démarrage | SPEC 4.7 | `node::setup()` |
| Variante par BOARD_SENSE | EF-07 | `node::setup()` |
| Heartbeat 2 s ± 250 ms, immédiat sur événement | PROTOCOL §5.1 | `node/src/node.cpp` |
| Apprentissage / oubli (30 s) du dongle | PROTOCOL §5.3 | `node/src/node.cpp` |
| Commandes, idempotence (16 derniers `cmd_id`), ACK unicast | PROTOCOL §6 | `node/src/node.cpp`, `common/src/auth.cpp` |
| Authentification HMAC + compteur persistant | PROTOCOL §7, A4 | `common/src/auth.cpp` |
| Balayage des canaux après 60 s sans réseau | SPEC 4.1, A5 | `node/src/node.cpp` |
| SW1 : ≥ 3 s maintenance, ≥ 10 s remise à zéro | SPEC 4.9, A6 | `node/src/node.cpp` |
| LED d'état (option) | SPEC 4.9, A7 | `node/src/node.cpp` |
| Maintenance AP+STA, page web, OTA avec retour arrière | SPEC 4.9 | `node/src/maintenance.cpp` |

## Recette sur banc (SPEC 8.3) : à faire sur les premières cartes

| # | Essai | Moyen | Critère |
|---|-------|-------|---------|
| B1 | Trame DMX : break, MAB, débit, 2 bits de stop, longueur `dmx_out_slots` | Analyseur logique sur DI du SP3485 (IO4) et sur A/B | break ≥ 88 µs (176 visé), MAB ≥ 8 µs (12 visé), 4 µs/bit |
| B2 | Cadence : trame immédiate sur donnée nouvelle, ≥ 10 ms d'écart, 44 Hz sans donnée | Analyseur ; dongle ou émetteur de test | intervalle break-break conforme |
| B3 | Relais : suit le canal (≥ 128), forçage, intervalle minimal 3 s différé, état au démarrage, perte de flux sans effet | Commandes + DMX | SPEC 4.5 points 1 à 5 |
| B4 | PWM : fréquence 4882 Hz, 14 bits, déphasage d'un quart de période entre canaux, gamma, fondu à la mise sous tension | Oscilloscope 4 voies sur IO3/6/7/10 | décalages 51 µs (¼ de 205 µs) |
| B5 | PWM à 0 dès la mise sous tension (pas d'impulsion) | Oscilloscope déclenché sur l'alimentation 5 V | aucune impulsion avant l'initialisation |
| B6 | Perte de flux : dernière trame conservée ; blackout après `loss_blackout_ms` si configuré | Couper le dongle | EF-06 |
| B7 | Maintenance : SW1 3 s, 3 mises sous tension, commande ; réception ESP-NOW maintenue en AP+STA [V-FW-05] ; sortie par page, par SW1, par délai | Téléphone + DMX | le DMX continue d'être rafraîchi |
| B8 | OTA : mise à jour par la page ; retour arrière si aucun paquet valide en 60 s | Deux images | l'ancienne image redémarre |
| B9 | Changement de canal par commande (appliqué 500 ms après l'ACK) ; balayage après 60 s sans réseau | Dongle sur un autre canal | le nœud retrouve le réseau et persiste le canal |
| B10 | Authentification : commande non signée refusée (`AUTH_FAILED`) une fois la clé posée, rejeu refusé, `IDENTIFY` toujours accepté | Démon Pi | PROTOCOL §7 |

## Dongle

- Liaison USB CDC avec le démon (PROTOCOL §8) : trames COBS, CRC16, `seq` par émetteur ;
  `UNIVERSE`, `COMMAND` (remorque d'authentification calculée par le Pi), `DONGLE_CONFIG`
  (persisté en NVS), `PING` → `PONG`, `GET_STATUS` → `STATUS` (aussi toutes les 5 s).
- Émission ESP-NOW **une à la fois** (attente du callback d'émission, garde de 50 ms),
  priorité COMMAND > DMX_DATA > BEACON (1 Hz, même sans univers) ; univers émis sur
  événement (≥ 10 ms d'écart) et rafraîchis à `refresh_hz` (44), arrêtés après
  `hold_timeout` (10 s) sans données du Pi ; mode v1 fragmenté sélectionnable.
- Commandes : ciblées, 5 tentatives (attentes 30, 60, 120, 240 ms puis 50 ms) jusqu'à
  l'ACK de la bonne MAC ; broadcast, 3 émissions à 20 ms puis 1 s de collecte ;
  `CMD_RESULT` au Pi. HEARTBEAT et ACK remontés en `RADIO_RX` (paquet brut) ; les
  heartbeats des nœuds non configurés (`net_id` 0) sont acceptés pour l'enrôlement.
- Sonde de latence : **D10 (GPIO10)** bascule à chaque émission radio (ENF-01).
- Logique testée nativement : `common/src/dongle.cpp`, `common/src/serial.cpp`.

### Recette dongle (SPEC 8.4)

| # | Essai | Critère |
|---|-------|---------|
| D1 | Latence Art-Net → ligne DMX : QLC+ → démon → dongle (sonde D10) → nœud (analyseur sur IO4) | ≤ budget SPEC §5.1 (≈ 3,3 ms typique en trame courte) |
| D2 | Débit USB : 4 univers à 50 Hz sans perte (`serial_errors`, `coalesced`) [V-FW-04] | aucune erreur série |
| D3 | Pi débranché : univers maintenus 10 s puis BEACON seul | `hold_timeout` |
| D4 | Commande ciblée vers un nœud éteint : 5 tentatives, `CMD_RESULT` = expiré | < 0,5 s |
