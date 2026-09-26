# Architecture Decision Records

Format : Statut, Contexte, Décision, Conséquences, Alternatives écartées.

Les ADR 0001 à 0010 reprennent les décisions de la section 3 du cahier des charges. Les ADR 0011 à 0015 sont issus de la spécification ; 0011, 0014 et 0015 ont été tranchés par arbitrage le 2026-09-25.

| ADR | Titre | Statut |
|-----|-------|--------|
| [0001](0001-transport-esp-now.md) | Transport radio ESP-NOW | Accepté (cahier des charges, décision 1) |
| [0002](0002-regie-pi-dongle.md) | Régie Raspberry Pi + QLC+ + dongle XIAO ESP32-C3 | Accepté (décision 2) |
| [0003](0003-microcontroleur-esp32-c3-mini-1.md) | Microcontrôleur ESP32-C3-MINI-1 | Accepté (décision 3) |
| [0004](0004-alimentation-isolee.md) | Alimentation interne isolée Mean Well IRM-03-5 | Accepté (décision 4 amendée par A1) |
| [0005](0005-relais-g5rl.md) | Relais de coupure Omron G5RL-1A-E-HR | Accepté (décision 5, amendée) |
| [0006](0006-rubans-alim-externe-pwm.md) | Rubans LED : alimentation externe, 4 PWM côté masse | Accepté (décision 6) |
| [0007](0007-pcb-secable.md) | PCB unique sécable par V-cut | Accepté (décision 7) |
| [0008](0008-borniers-wago-2604.md) | Borniers WAGO série 2604 | Accepté (décision 8) |
| [0009](0009-relais-par-canal-dmx.md) | Commande du relais par un canal DMX | Accepté (décision 9) |
| [0010](0010-boitier-imprime-3d.md) | Boîtier imprimé 3D paramétrique | Accepté (décision 10) |
| [0011](0011-esp-now-v2-trame-unique.md) | ESP-NOW v2, un univers par paquet, plateforme pioarduino | Accepté (arbitrage A8, 2026-09-25) |
| [0012](0012-liaison-serie-cobs.md) | Liaison série Pi ↔ dongle encadrée COBS + CRC16 | Accepté (validation de la spec, 2026-09-25) |
| [0013](0013-commandes-broadcast-ack.md) | Commandes en broadcast avec acquittement applicatif | Accepté (validation de la spec, 2026-09-25) |
| [0014](0014-trames-dmx-evenement.md) | Émission DMX sur événement et longueur de trame configurable | Accepté (arbitrage A3 : défaut 512, 2026-09-25) |
| [0015](0015-authentification-commandes.md) | Authentification des commandes par HMAC tronqué | Accepté (arbitrage A4, 2026-09-25) |
