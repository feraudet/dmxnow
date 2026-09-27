# dmxnow — démon et CLI Raspberry Pi (livrable 8.5)

```
QLC+ ──Art-Net 127.0.0.1:6454──▶ dmxnowd ──USB, trames COBS──▶ dongle ──ESP-NOW──▶ nœuds
                                    ▲
                     dmxnow (CLI) ──┘ socket /run/dmxnow/control.sock
```

- **dmxnowd** : reçoit l'Art-Net (ArtDmx), répond aux ArtPoll (ArtPollReply, 4 univers par
  réponse), transmet les univers configurés au dongle, pousse la configuration radio au
  dongle à chaque (re)connexion, rouvre le port après 3 s sans PONG ou sur débranchement,
  tient la table des nœuds (heartbeats), exécute les commandes de la CLI et les signe
  (HMAC, compteur persistant strictement croissant) quand une clé réseau existe (A4).
- **dmxnow** : CLI (EF-13).
- Dépendance unique : `pyserial` ; Python ≥ 3.11 (Raspberry Pi OS Bookworm).

## Installation

```
git clone … && cd dmxnow/pi
# brancher le dongle (firmware firmware/dongle flashé), puis :
sudo ./install.sh
```

L'installeur (idempotent : le relancer met à jour, en gardant configuration, clé et
compteurs) :
- crée l'utilisateur système `dmxnow` (groupe `dialout`) et le venv `/opt/dmxnow` ;
- écrit `/etc/dmxnow/dmxnowd.toml` avec un `net_id` **aléatoire** s'il n'existe pas ;
- génère la clé réseau `/etc/dmxnow/net_key` (32 octets, lisible par `dmxnow` seul) ;
  `--no-key` pour s'en passer (commandes non signées) ;
- détecte le dongle branché (USB `303a:1001`) et écrit la règle udev
  `/dev/dmx-dongle` sur son numéro de série ; `--dongle-serial MAC` sinon ;
- installe et démarre `dmxnowd.service` (`Restart=always`, `RestartSec=1`).

Pour utiliser la CLI sans `sudo` : `sudo usermod -a -G dmxnow $USER` puis se reconnecter.

## Configuration de QLC+

Entrées/Sorties → univers → sortie **Art-Net**, interface `127.0.0.1`, univers Art-Net =
un des `universes` de `/etc/dmxnow/dmxnowd.toml`. Transmission « Complète » recommandée
[V-FW-08].

## CLI

| Commande | Effet |
|----------|-------|
| `dmxnow nodes` | Nœuds entendus : nom, MAC, variante, univers, adresse, trame DMX, RSSI, pertes, relais (`*` = forcé), uptime, version, âge du dernier heartbeat. Signale `NOT ENROLLED`, `SILENT`, `MAINTENANCE`, et les nœuds restés à 512 canaux (A3). |
| `dmxnow status` | Démon, dongle (canal, débit, émissions, erreurs série, fusions), statistiques Art-Net. |
| `dmxnow enroll node-3A4F21 --universe 0 --address 17 --name lyre-cour --slots 40` | Rattache un nœud neuf au réseau : `net_id`, clé réseau, univers, adresse, nom, trame courte. |
| `dmxnow identify lyre-cour [-d 10]` | Fait clignoter le nœud (et son canal `identify_slot`). `all` = tous. |
| `dmxnow set lyre-cour universe=1 start_address=33 dmx_out_slots=48` | `SET_CONFIG` (clés de PROTOCOL §6.4). |
| `dmxnow get lyre-cour` | `GET_CONFIG` (secrets exclus). |
| `dmxnow relay lyre-cour on\|off\|auto` | Force le relais ou le rend au canal DMX. |
| `dmxnow maintenance lyre-cour [-t 600]` | Point d'accès `dmxnow-<nom>` + page web + OTA. |
| `dmxnow reboot lyre-cour` · `dmxnow factory-reset lyre-cour --yes` | |
| `dmxnow dongle-config channel=11 power_dbm=15` | Réglage radio du dongle à chaud (non écrit dans le fichier). |

Les cibles s'écrivent par MAC, par nom ou `all`. `--json` donne la réponse brute.

## Changer de canal radio

1. `dmxnow set all radio_channel=11` (les nœuds changent 500 ms après leur ACK) ;
2. `channel = 11` dans `/etc/dmxnow/dmxnowd.toml`, puis `sudo systemctl restart dmxnowd`.
Un nœud qui a manqué la commande retrouve seul le réseau par balayage au bout de 60 s (A5).

## Puissance d'émission

Avec l'antenne dipôle 5 dBi du boîtier du dongle, `power_dbm = 15` donne environ
20 dBm PIRE, la limite européenne en 2,4 GHz : ne pas l'augmenter (le démon journalise un
avertissement au-delà de 15).

## Développement et tests

```
pip install -e '.[test]'
pytest                       # 46 tests : protocole contre les vecteurs communs, Art-Net,
                             # démon contre un dongle simulé (pseudo-terminal), reconnexion,
                             # CLI, authentification, enrôlement
ci/test_install.sh           # install.sh dans Debian Bookworm + systemd (docker)
```
