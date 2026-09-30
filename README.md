# dmxnow

Wireless DMX and LED strip nodes over ESP-NOW, driven by QLC+ from a Raspberry Pi.
One mains cable per fixture: DMX arrives by radio, the node switches the fixture's
power and drives 4 LED strip channels.

Nœuds DMX et rubans LED sans fil, sur ESP-NOW, pilotés par QLC+ depuis un Raspberry Pi.
Un seul câble secteur par projecteur : le DMX arrive par radio, le nœud coupe
l'alimentation du projecteur et pilote 4 canaux de rubans LED.

| | |
|---|---|
| 🇬🇧 **[Read in English](README.en.md)** | context, the need, use cases, how it works, status |
| 🇫🇷 **[Lire en français](README.fr.md)** | contexte, besoin, cas d'usage, fonctionnement, état du projet |

![dmxnow board v0.3 (JLCPCB render)](docs/figures/jlcpcb-top.png)

🔴 230 V mains device: read [docs/securite.md](docs/securite.md) first.
Appareil raccordé au 230 V : lire [docs/securite.md](docs/securite.md) avant tout.

Hardware CERN-OHL-S-2.0, software GPL-3.0-or-later: [LICENSE](LICENSE).
