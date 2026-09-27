# Fonctionnement, principes, options

Ce document explique **comment dmxnow marche** : qui parle à qui, ce que fait chaque
carte, et quelles fonctions et options existent. Les diagrammes s'affichent directement
sur GitHub. Les figures sont générées depuis les données du projet par
[`figures/make_figures.py`](figures/make_figures.py).

Détail normatif : [SPEC](../spec/SPEC.md) et [PROTOCOL](../spec/PROTOCOL.md). Mode
d'emploi : [mise-en-service.md](mise-en-service.md).

- [1. Vue d'ensemble](#1-vue-densemble)
- [2. Le chemin d'une valeur DMX](#2-le-chemin-dune-valeur-dmx)
- [3. La radio](#3-la-radio)
- [4. Le nœud](#4-le-nœud)
- [5. Le relais](#5-le-relais)
- [6. Les rubans LED](#6-les-rubans-led)
- [7. Commandes, enrôlement, sécurité](#7-commandes-enrôlement-sécurité)
- [8. Maintenance et mise à jour](#8-maintenance-et-mise-à-jour)
- [9. Le dongle et le Raspberry Pi](#9-le-dongle-et-le-raspberry-pi)
- [10. Options](#10-options)

---

## 1. Vue d'ensemble

```mermaid
flowchart LR
    subgraph PI["Raspberry Pi"]
        QLC["QLC+"] -- "Art-Net<br/>127.0.0.1:6454" --> D["dmxnowd<br/>(démon)"]
        CLI["dmxnow<br/>(CLI)"] <-- "socket Unix" --> D
    end
    D <-- "USB<br/>trames COBS + CRC" --> DG["Dongle<br/>XIAO ESP32-C3<br/>+ antenne 5 dBi"]
    DG == "ESP-NOW broadcast<br/>univers DMX, commandes, balise" ==> N1 & N2 & N3
    N1 & N2 & N3 -. "unicast<br/>heartbeat, accusés" .-> DG
    subgraph N1["Nœud 1 (carte entière)"]
        direction TB
        a1["sortie DMX filaire"]
        b1["relais 230 V"]
        c1["4 PWM rubans"]
    end
    subgraph N2["Nœud 2 (carte cassée)"]
        direction TB
        a2["sortie DMX filaire"]
        b2["relais 230 V"]
    end
    N3["Nœud n …"]
    a1 --> P1["Projecteur"]
    b1 --> P1
    c1 --> S1["Rubans LED"]
    a2 --> P2["Projecteur"]
    b2 --> P2
```

| Élément | Rôle en une phrase |
|---------|--------------------|
| **QLC+** | Le pupitre logiciel : produit les univers DMX en Art-Net. |
| **dmxnowd** | Reçoit l'Art-Net, l'envoie au dongle, suit les nœuds, exécute et signe les commandes. |
| **dmxnow** (CLI) | Commandes d'exploitation : lister, enrôler, identifier, régler, forcer le relais, maintenance. |
| **Dongle** | Pont USB ↔ radio : diffuse les univers et les commandes, remonte heartbeats et accusés. |
| **Nœud** | Au pied de chaque projecteur : recrée une ligne DMX filaire, coupe ou rétablit le 230 V, pilote des rubans. |

**Principe clé** : un seul émetteur (le dongle), des récepteurs passifs. La radio
diffuse chaque univers en entier à tous les nœuds ; chaque nœud prend son univers et
ignore le reste. Ajouter un nœud ne coûte rien en radio.

## 2. Le chemin d'une valeur DMX

```mermaid
sequenceDiagram
    autonumber
    participant Q as QLC+
    participant D as dmxnowd
    participant G as Dongle
    participant N as Nœud
    participant P as Projecteur
    Q->>D: ArtDmx (univers 0, 512 octets)
    D->>G: UNIVERSE (COBS + CRC, USB)
    G-->>N: DMX_DATA broadcast (1 paquet = 1 univers)
    Note over N: vérifie version, net_id, univers, CRC
    N->>P: trame DMX filaire (dès réception, puis 44 Hz)
    loop sans nouvelle donnée
        G-->>N: DMX_DATA répété à 44 Hz
        N->>P: trame rafraîchie à 44 Hz
    end
```

Chaque étape émet **sur événement** (dès qu'une valeur change, avec au moins 10 ms
d'écart) et **rafraîchit** à 44 Hz sans changement. Une trame radio perdue est corrigée
par la suivante, 23 ms plus tard au pire.

![Latence typique](figures/latence.svg)

L'essentiel de la latence est l'attente de la fin de la trame DMX en cours sur le câble.
D'où l'option **trame courte** (`dmx_out_slots`) : le nœud n'émet que jusqu'au dernier
canal utile du projecteur.

![Trame DMX](figures/trame-dmx.svg)

## 3. La radio

**ESP-NOW** : des trames Wi-Fi brutes entre puces Espressif, sans point d'accès ni
connexion. dmxnow utilise ESP-NOW **v2** (jusqu'à 1470 octets) : un univers complet (512
canaux + 18 octets d'en-tête) tient dans **un seul paquet**. Un univers n'est donc jamais
appliqué à moitié.

| Message | Sens | Adressage | Rythme | Contenu |
|---------|------|-----------|--------|---------|
| `DMX_DATA` | dongle → nœuds | broadcast | ≥ 44 Hz par univers | 512 canaux |
| `BEACON` | dongle → nœuds | broadcast | 1 Hz | « le réseau est là », même QLC+ arrêté |
| `COMMAND` | dongle → nœud(s) | broadcast, cible dans le paquet | à la demande, répété | identifier, régler, relais… |
| `ACK` | nœud → dongle | unicast | en réponse | résultat de la commande |
| `HEARTBEAT` | nœud → dongle | unicast | 2 s ± 250 ms | état complet du nœud |

```mermaid
flowchart TB
    subgraph Paquet["Paquet radio (en-tête commun, 18 octets)"]
        direction LR
        h1["magic 'DN'<br/>version"] --- h2["type"] --- h3["net_id<br/>(réseau)"] --- h4["univers"] --- h5["seq<br/>(pertes)"] --- h6["offset, longueur,<br/>flags"] --- h7["CRC-16"]
    end
    Paquet --> V{"Validation à la réception<br/>(ordre imposé)"}
    V -- "magic, version, autre net_id,<br/>taille, CRC, type inconnu" --> X["rejeté<br/>(compté)"]
    V -- "valide" --> OK["copié dans la file<br/>de la tâche principale"]
    OK --> U{"DMX_DATA<br/>de son univers ?"}
    U -- oui --> DMX["sortie DMX, relais, rubans"]
    U -- non --> I["ignoré"]
```

**Canal** : un canal Wi-Fi fixe (1, 6 ou 11 recommandés), commun au dongle et aux
nœuds. **Occupation** : environ 4 % du canal par univers à 6 Mbit/s ; limite
recommandée **4 univers par dongle**.

**Auto-réparation** : un nœud qui n'entend plus son réseau pendant **60 s** balaie les
canaux 1 à 13 (300 ms par canal) jusqu'à retrouver son `net_id`, puis adopte ce canal.
Pendant ce temps, il continue d'émettre la dernière trame DMX.

## 4. Le nœud

![Carte du nœud](figures/carte.svg)

```mermaid
flowchart LR
    subgraph M["230 V (couvercle orange)"]
        J1["J1 entrée<br/>L, N"] --> F1["F1 T500 mA<br/>RV1 varistance"]
        F1 --> PS1["PS1 alimentation<br/>isolée 5 V"]
        J1 -- "L" --> K1["K1 relais<br/>16 A"]
        K1 -- "L commutée" --> J4["J4 sortie 1"] & J7["J7 sortie 2"]
        J1 -- "N (non coupé)" --> J4 & J7
    end
    subgraph B["Basse tension (couvercle bleu)"]
        PS1 == "isolement<br/>renforcé" ==> V5["+5 V → régulateur 3,3 V"]
        V5 --> U1["ESP32-C3<br/>radio + logique"]
        U1 --> Q1["pilote relais"] --> K1
        U1 --> U2["SP3485<br/>+ protection"] --> J2["J2 → XLR-3<br/>vers le projecteur"]
        SW1["SW1 poussoir"] --> U1
        J3["J3 programmation<br/>(hors secteur)"] --> U1
    end
    subgraph S["Rubans 12/24 V (partie sécable)"]
        J5["J5 alim. LED"] --> F2["F2 20 A"] --> J6["J6 V+ commun"]
        U1 -- "4 PWM" --> U4["U4 5 V"] --> Q["Q2..Q5<br/>MOSFET"] --> J68["J6/J8 canaux 1-4"]
    end
    PE["3 × PE"] --> W["WAGO 221-413<br/>(hors carte)"]
```

- **Une carte, deux variantes** : la carte est livrée entière ; on scie la partie rubans
  si on n'en a pas besoin. Le firmware reconnaît la variante au démarrage (BOARD_SENSE).
- **Isolement** : tout le 230 V est à gauche de la barrière (fentes fraisées, ≥ 6 mm de
  cuivre à cuivre, cloison du boîtier) ; seul PS1 la franchit, par son isolement
  interne certifié. 🔴 [securite.md](securite.md)
- **Rien de métallique près de l'antenne** (hachures) : pas de vis ni d'insert à moins
  de 15 mm.

### Cycle de vie du nœud

```mermaid
stateDiagram-v2
    [*] --> Demarrage
    Demarrage: Démarrage<br/>PWM à 0 en premier, relais à son état de démarrage
    Demarrage --> NonEnrole: net_id = 0 (neuf)
    Demarrage --> Recherche: net_id connu
    NonEnrole: Non enrôlé<br/>n'accepte que la configuration
    NonEnrole --> Recherche: dmxnow enroll
    Recherche: Recherche du réseau
    Recherche --> Connecte: BEACON ou DMX de son net_id
    Connecte: Connecté<br/>dongle appris, heartbeats en unicast
    Connecte --> Flux: DMX de son univers
    Flux: Flux DMX<br/>trame émise, relais et rubans suivent
    Flux --> Connecte: plus de DMX<br/>(dernière trame conservée ou noir)
    Connecte --> Recherche: 30 s sans dongle
    Recherche --> Balayage: 60 s sans réseau
    Balayage: Balayage des canaux 1 à 13
    Balayage --> Connecte: net_id retrouvé<br/>(canal mémorisé)
```

En parallèle de ces états : **maintenance** (point d'accès + page web, §8) et
**identification** (clignotement), qui n'interrompent pas la sortie DMX.

## 5. Le relais

Le relais coupe la **phase** des deux sorties 230 V (projecteur, alimentation des
rubans). Qui décide ?

```mermaid
flowchart TD
    A{"Forçage par commande ?<br/>dmxnow relay on/off"} -- oui --> F["État forcé<br/>(perdu au redémarrage)"]
    A -- "non (auto)" --> B{"relay_dmx = 1<br/>et flux DMX présent ?"}
    B -- oui --> C{"canal start_address ≥ 128 ?"}
    C -- oui --> ON["allumé"]
    C -- non --> OFF["éteint"]
    B -- non --> K["garde son état<br/>(au démarrage : relay_power_on)"]
    F & ON & OFF & K --> T{"dernière commutation<br/>il y a ≥ 3 s ?"}
    T -- oui --> S["commute maintenant"]
    T -- non --> W["commutation différée<br/>à l'échéance"]
```

![Anti-rebond du relais](figures/relais.svg)

- Le canal agit sur un **niveau** (≥ 128 allumé), pas sur un front.
- **Perte du flux** : le relais ne bouge pas (un projecteur ne s'éteint pas parce que le
  Pi redémarre).
- L'état est mémorisé à chaque commutation effective, ainsi qu'un compteur de
  commutations visible dans `dmxnow nodes`.

## 6. Les rubans LED

Quatre sorties à MOSFET côté masse, pour rubans à **anode commune** 12 ou 24 V (RGB,
RGBW ou quatre rubans blancs). 6 A par canal, 16 A au total.

![Déphasage PWM](figures/pwm-dephasage.svg)

| Fonction | Principe | Réglage |
|----------|----------|---------|
| **PWM 4882 Hz, 14 bits** | Au-dessus du seuil de scintillement visible et des caméras courantes ; 16 384 niveaux | `pwm_freq_hz` (≤ 19,5 kHz, résolution déduite) |
| **Déphasage** | Les 4 canaux commencent chacun un quart de période plus tard : les appels de courant s'étalent | automatique |
| **Gamma** | Corrige la perception de l'œil : les faibles valeurs DMX restent fines | `gamma_x10` (10 = linéaire, 22 défaut) |
| **8 ou 16 bits** | 16 bits = 2 canaux DMX par couleur, fondus très lents sans paliers | `pwm_mode` |
| **Fondu à l'allumage** | Rampe à la mise sous tension et à chaque rallumage du relais | `fade_on_ms` (500) |
| **Démarrage propre** | Les PWM sont mises à 0 avant toute autre chose : pas de flash au démarrage | automatique |

![Gamma](figures/gamma.svg)

## 7. Commandes, enrôlement, sécurité

Les commandes ne sont pas répétées en continu comme le DMX. Elles sont donc
**acquittées et retransmises** :

```mermaid
sequenceDiagram
    participant C as CLI
    participant D as dmxnowd
    participant G as Dongle
    participant N as Nœud
    C->>D: relay lyre-cour on
    Note over D: signature HMAC-SHA256<br/>(clé réseau + compteur)
    D->>G: COMMAND + signature
    G-->>N: tentative 1
    Note over G: pas d'accusé en 30 ms
    G-->>N: tentative 2 (après 60 ms)
    N->>N: vérifie la signature et le compteur<br/>exécute une seule fois
    N->>G: ACK OK (unicast)
    G->>D: CMD_RESULT OK
    D->>C: OK
```

- Ciblée : **5 tentatives** (30, 60, 120, 240 ms), moins de 0,5 s en tout.
- `all` : 3 émissions à 20 ms d'intervalle, puis 1 s de collecte des accusés.
- Un doublon n'est jamais exécuté deux fois (le nœud mémorise les 16 dernières commandes).

### Enrôlement

```mermaid
sequenceDiagram
    participant D as dmxnowd
    participant N as Nœud neuf
    N-->>D: HEARTBEAT broadcast (net_id 0, « node-3A4F21 »)
    Note over D: dmxnow nodes : NOT ENROLLED
    D->>N: SET_CONFIG net_id, univers, adresse, nom,<br/>dmx_out_slots, clé réseau
    N->>D: ACK OK
    Note over N: écoute désormais son net_id<br/>et exige des commandes signées
    N-->>D: HEARTBEAT unicast (lyre-cour)
```

**Ce qui est protégé** : une commande (relais, maintenance, remise à zéro, réglage)
n'est acceptée que signée par le Pi qui détient la clé ; une commande rejouée est
refusée. `IDENTIFY`, inoffensive, reste libre. Le flux DMX n'est pas signé : la menace
visée est l'erreur (deux installations voisines), pas le sabotage d'un spectacle.

## 8. Maintenance et mise à jour

```mermaid
flowchart LR
    A["dmxnow maintenance"] --> M
    B["SW1 ≥ 3 s"] --> M
    C["3 mises sous tension<br/>à moins de 5 s"] --> M
    M["Maintenance<br/>point d'accès dmxnow-nom<br/>(WPA2, même canal)"] --> W["http://192.168.4.1<br/>état, réglages, relais"]
    W --> O["Téléverser firmware.bin"]
    O --> R["Redémarrage sur<br/>la nouvelle image"]
    R --> V{"paquet radio valide<br/>en 60 s ?"}
    V -- oui --> OK["image confirmée"]
    V -- non --> RB["retour automatique<br/>à l'ancienne image"]
    S["SW1 ≥ 10 s"] --> FR["remise à zéro usine<br/>(clé et mot de passe compris)"]
```

La réception ESP-NOW continue pendant la maintenance : le projecteur reste piloté.

## 9. Le dongle et le Raspberry Pi

```mermaid
flowchart LR
    subgraph G["Dongle"]
        direction TB
        RX["USB : décodage COBS, CRC"] --> Q{"file d'émission<br/>par priorité"}
        Q -- "1" --> CMD["COMMAND"]
        Q -- "2" --> DMX["DMX_DATA<br/>sur événement + 44 Hz"]
        Q -- "3" --> BC["BEACON 1 Hz"]
        CMD & DMX & BC --> TX["ESP-NOW<br/>un paquet à la fois"]
    end
```

| Comportement | Valeur |
|--------------|--------|
| Pi silencieux (démon arrêté, USB coupé) | le dongle maintient les univers **10 s** (`hold_timeout_ms`), puis seulement la balise |
| Liaison USB surveillée | `PING` chaque seconde ; réouverture du port après 3 s sans réponse |
| Démon planté | redémarré par systemd en 1 s |
| Dongle identifié | `/dev/dmx-dongle` par son numéro de série (plusieurs ESP32 sur le même Pi possibles) |
| Découverte Art-Net | réponse aux ArtPoll : QLC+ voit dmxnow comme un nœud Art-Net |

## 10. Options

### Matériel

```mermaid
flowchart TD
    Q1{"Des rubans LED<br/>à piloter ?"} -- oui --> E["Carte entière<br/>boîtier full 208 × 88 × 34 mm"]
    Q1 -- non --> C["Carte cassée (sciée)<br/>boîtier cut 150 × 88 × 34 mm"]
    E & C --> Q2{"Besoin d'un voyant<br/>d'état ?"}
    Q2 -- oui --> L["D4 + R19 montées (BOM _led)<br/>couvercle lid_lv_light_pipe<br/>status_led = 1"]
    Q2 -- non --> N["sans LED (défaut)"]
```

| Carte entière (`full`) | Carte cassée (`cut`) |
|:---:|:---:|
| ![Boîtier full fermé](../enclosure/out/full/assembly_closed.png) | ![Boîtier cut fermé](../enclosure/out/cut/assembly_closed.png) |
| ![Boîtier full ouvert](../enclosure/out/full/assembly_open.png) | ![Boîtier cut ouvert](../enclosure/out/cut/assembly_open.png) |

| Dongle |
|:---:|
| ![Boîtier du dongle](../enclosure/out/dongle/assembly_closed.png) |

### Réglages du nœud

| Famille | Clé | Défaut | Choix |
|---------|-----|--------|-------|
| Adressage | `universe`, `start_address` | 0, 1 | univers et premier canal du nœud (relais puis rubans) |
| | `dmx_out_slots` | 512 | longueur de la trame DMX : 512 = compatible, courte = rapide |
| | `identify_slot` | 0 | canal forcé à 255/0 pendant l'identification (0 = aucun) |
| Relais | `relay_dmx` | 1 | suit le canal DMX, ou commande seule |
| | `relay_power_on` | 2 | au démarrage : éteint, allumé, dernier état |
| | `relay_min_interval_ms` | 3000 | intervalle minimal entre commutations |
| Perte de flux | `loss_blackout_ms` | 0 | 0 = garder la dernière trame ; sinon noir après ce délai |
| Rubans | `pwm_mode`, `gamma_x10`, `fade_on_ms`, `pwm_freq_hz` | 0, 22, 500, 4882 | §6 |
| Radio | `radio_channel`, `net_id` | 6, 0 | canal et réseau |
| Maintenance | `maint_password` | aléatoire | mot de passe du point d'accès (écriture seule) |
| | `powercycle_maint` | 1 | trois mises sous tension ouvrent la maintenance |
| Voyant | `status_led` | 0 | 1 si D4 est montée |

### Réglages du dongle et du démon (`/etc/dmxnow/dmxnowd.toml`)

| Clé | Défaut | Choix |
|-----|--------|-------|
| `universes` | `[0]` | univers Art-Net transmis (4 au plus conseillé) |
| `channel` | 6 | canal radio |
| `phy_rate` | `6M` | débit radio : 6M (défaut), 12M, 24M, ou 1M à 11M (plus de portée, plus d'occupation) |
| `power_dbm` | 15 | puissance ; 15 dBm + antenne 5 dBi ≈ 20 dBm PIRE, limite européenne |
| `mode` | `v2` | `v2` = un paquet par univers ; `v1` = fragmenté (compatibilité) |
| `refresh_hz`, `hold_timeout_ms` | 44, 10000 | rafraîchissement et maintien sans Pi |
| clé réseau | générée | `install.sh --no-key` : commandes non signées (déconseillé) |

### Voyant d'état (option D4)

| Voyant | Signification |
|:------:|---------------|
| ● fixe | flux DMX reçu |
| ◐ 1 Hz | réseau entendu, pas de DMX |
| ●● double éclat | aucun dongle |
| ✱ 5 Hz | maintenance |
