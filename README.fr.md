# dmxnow

[English](README.en.md) · **Français**

Nœuds DMX et rubans LED sans fil, sur ESP-NOW, pilotés par QLC+ depuis un Raspberry Pi.

![Carte dmxnow v0.3, face top (rendu JLCPCB)](docs/figures/jlcpcb-top.png)

## Contexte

En scénographie (expositions, musées, spectacles, événements), les projecteurs sont
souvent loin de la régie : accrochés au plafond, répartis dans plusieurs salles,
cachés dans un décor. Chacun a besoin de deux câbles : le secteur, et une ligne DMX qui
part de la console, passe d'un projecteur à l'autre et se termine par un bouchon. Tirer
et cacher ces lignes DMX coûte du temps à chaque montage, et elles cassent ou se
débranchent.

Le parc visé : lyres, projecteurs COB et projecteurs classiques jusqu'à 200 W, plus des
rubans LED 12/24 V dans les décors, le tout piloté par QLC+.

## Le besoin

- **Un seul câble par projecteur** : le secteur. Le DMX arrive par radio.
- **Couper l'alimentation d'un projecteur depuis QLC+**, sans prise commandée ni bloc de
  relais à part : hors séance, pour ne pas laisser tourner les ventilateurs ni consommer
  en veille.
- **Piloter des rubans LED** dans le même spectacle que les projecteurs, sans contrôleur
  LED séparé.
- **Une latence invisible** : moins de 10 ms en typique quand la trame DMX est réglée
  sur les canaux utilisés par le projecteur (environ 13 ms en trame complète de
  512 canaux), et un rafraîchissement DMX normal (44 Hz).
- **Pas de réglage sur place** : un nœud se configure depuis le Pi, se retrouve seul sur
  le réseau et s'identifie à distance (ses rubans ou sa LED d'état clignotent).
- **Un coût par projecteur raisonnable** : environ 53 € de matière pour un nœud avec
  rubans, 39 € sans, en série de 20.
- **Un matériel sûr** : le nœud est au 230 V, son isolement est au cœur de la conception.

La plupart des récepteurs DMX sans fil du commerce ne font que le DMX : ils ne coupent
pas l'alimentation du projecteur et ne pilotent pas de rubans.

## Cas d'usage

| Situation | Ce que dmxnow apporte |
|-----------|-----------------------|
| **Exposition ou musée scénographié** : projecteurs sur rails, répartis dans plusieurs salles | Chaque projecteur se branche sur la prise la plus proche ; plus de ligne DMX qui court d'une salle à l'autre |
| **Spectacle ou événement en tournée** : montage et démontage chaque jour | Moins de câbles à tirer et à cacher ; un nœud neuf s'enrôle en une commande |
| **Décor lumineux** : rubans LED dans un meuble, une vitrine, un élément de décor | Les 4 canaux de rubans suivent QLC+ comme un projecteur (RGBW, gamma, 8 ou 16 bits) |
| **Fin de séance** : couper tout le parc sans monter à l'échelle | Le relais de chaque nœud suit un canal DMX, ou une commande `dmxnow relay` |
| **Installation permanente** : lumière automatique dans un lieu ouvert au public | Le Pi et QLC+ tournent seuls ; un nœud éteint puis rallumé retrouve le réseau et son canal radio sans intervention |
| **Projecteur accroché en hauteur** : maintenance sans décrocher | Mise à jour du firmware par Wi-Fi (OTA) et page de réglage, boîtier fermé |

## Comment ça marche

![Vue d'ensemble : QLC+, démon, dongle, nœuds](docs/diagrams/vue-ensemble.png)

- **QLC+** envoie de l'Art-Net en local au démon **`dmxnowd`**, sur le Raspberry Pi.
- Le démon passe les univers par USB à un **dongle** (XIAO ESP32-C3, antenne 5 dBi).
- Le dongle les diffuse en **ESP-NOW** : un paquet par univers, dès qu'une valeur change,
  et répété à 44 Hz. 4 univers par dongle conseillés, 8 au plus.
- Chaque **nœud** (ESP32-C3) garde son univers, sort la trame DMX, suit son canal de
  relais et ses canaux de rubans, et renvoie un heartbeat au Pi.
- Les commandes (`dmxnow relay`, `set`, `reboot`...) sont signées (HMAC-SHA256) et
  acquittées.

Le détail illustré est dans [docs/fonctionnement.md](docs/fonctionnement.md).

## Deux variantes, une seule carte

| Variante | Usage | Boîtier |
|----------|-------|---------|
| Carte entière | projecteur + 4 canaux de rubans LED | 208 × 88 × 34 mm |
| Carte cassée | projecteur seul (partie rubans retirée) | 150 × 88 × 34 mm |

La partie rubans tient par trois onglets sécables qui portent ses pistes. Le nœud
détecte seul la variante.

## État du projet

| Livrable | État |
|----------|------|
| Spécification, protocole, décisions ([spec/](spec/)) | Validés (v1.0) |
| Carte v0.3 ([hardware/](hardware/)) | Commandée chez JLCPCB, 5 cartes montées, placement à valider |
| Firmware du nœud et du dongle ([firmware/](firmware/)) | Écrits, compilés et testés en CI |
| Démon et CLI du Pi ([pi/](pi/)) | Écrits, 50 tests (dongle simulé) |
| Boîtiers imprimés ([enclosure/](enclosure/)) | Nœud (2 variantes) et dongle, STL et STEP |
| Documentation ([docs/](docs/)) | Assemblage, flash, câblage, mise en service, sécurité |

Reste à mesurer sur banc à l'arrivée des cartes : portée et pertes radio, latence, charge
du dongle à 8 univers, timings DMX à l'analyseur logique, essais secteur du prototype.
La liste complète est dans [spec/SPEC.md](spec/SPEC.md) (points « À valider »).

## Par où commencer

| Je veux... | Lire |
|------------|------|
| Comprendre le système | [docs/fonctionnement.md](docs/fonctionnement.md) |
| Monter et installer des nœuds | [docs/README.md](docs/README.md), dans l'ordre : sécurité, assemblage, flash, câblage, mise en service |
| Installer le Pi | [pi/README.md](pi/README.md) |
| Refaire la carte | [hardware/README.md](hardware/README.md), commande JLCPCB : [hardware/ORDER.md](hardware/ORDER.md) |
| Imprimer les boîtiers | [enclosure/README.md](enclosure/README.md) |
| Modifier le firmware | [firmware/README.md](firmware/README.md) |

## Organisation du repo

| Dossier | Contenu |
|---------|---------|
| `spec/` | [SPEC.md](spec/SPEC.md), [PROTOCOL.md](spec/PROTOCOL.md), décisions d'architecture ([spec/adr/](spec/adr/)) |
| `hardware/` | Carte KiCad générée par script, gerbers, BOM et placement JLCPCB |
| `firmware/` | `common/` (protocole, testé sur PC), `node/` (nœud), `dongle/` (dongle USB) |
| `pi/` | Démon `dmxnowd`, CLI `dmxnow`, service systemd, règle udev, `install.sh` |
| `enclosure/` | Boîtiers CadQuery paramétriques, STL et STEP |
| `docs/` | Documentation d'utilisation, figures et diagrammes |

## Sécurité

🔴 Le nœud est raccordé au **230 V**. Lire [docs/securite.md](docs/securite.md) avant toute
manipulation. Toute la partie secteur (carte, boîtier, câblage) doit être relue par une
personne qualifiée avant fabrication et mise sous tension. Ce projet est fourni sans
aucune garantie.

## Licence

Matériel (carte, boîtiers, documentation) sous **CERN-OHL-S-2.0**, logiciel (firmware,
démon, CLI) sous **GPL-3.0-or-later**, bibliothèques KiCad tierces sous CC-BY-SA-4.0.
Détail dans [LICENSE](LICENSE).
