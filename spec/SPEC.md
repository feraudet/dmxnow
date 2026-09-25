# dmxnow — Spécification

Statut : **v0.2 — arbitrages A1 à A8 tranchés le 2026-09-25, en attente de validation finale**. Aucune implémentation ne démarre
avant validation de ce document, de [PROTOCOL.md](PROTOCOL.md) et des [ADR](adr/).

Conventions :
- 🔴 **RELECTURE HUMAINE OBLIGATOIRE** : section touchant au 230 V ou à la sécurité des
  personnes ; à faire relire par une personne qualifiée (électricien ou électronicien de
  puissance) avant fabrication et avant toute mise sous tension.
- **[ARBITRAGE Ax]** : point qui a fait l'objet d'un arbitrage (décisions en §9).
- **[V-xx]** : hypothèse non vérifiée, listée en §10 avec la source à consulter.
- Identifiants d'exigence : `EF-` fonctionnelle, `ENF-` non fonctionnelle, `ES-` sécurité.

---

## 1. Objet et périmètre

Système de diffusion DMX sans fil pour installations scénographiques : derrière chaque
projecteur, un seul câble secteur. Un nœud monté sur le cordon reçoit l'univers DMX par
ESP-NOW, le restitue en DMX filaire, commute l'alimentation du projecteur et, en version
carte entière, pilote 4 canaux PWM de rubans LED alimentés par une alimentation externe.

Dans le périmètre : PCB, firmware nœud, firmware dongle, démon Pi, boîtier, documentation.

Hors périmètre (repris du cahier des charges) : compatibilité CRMX/W-DMX, RDM,
alimentation LED intégrée, Wi-Fi/Art-Net en exploitation (Wi-Fi seulement en
maintenance), commande indépendante projecteur/rubans (un seul relais), plusieurs dongles
sur un même réseau, codes de départ DMX non nuls.

---

## 2. Exigences

### 2.1 Fonctionnelles

| ID     | Exigence |
|--------|----------|
| EF-01  | Le démon Pi reçoit l'Art-Net émis par QLC+ sur 127.0.0.1 (UDP 6454) et sur les interfaces configurées, et répond aux ArtPoll. sACN (E1.31) optionnel. |
| EF-02  | Le démon transmet chaque univers configuré au dongle par USB (PROTOCOL §8), gère la déconnexion et la reconnexion du dongle. |
| EF-03  | Le dongle diffuse chaque univers en ESP-NOW broadcast selon la règle « événement + 44 Hz minimum » (PROTOCOL §4.4) et continue d'émettre la dernière trame pendant `hold_timeout` (défaut 10 s) si le Pi se tait. |
| EF-04  | Le nœud filtre par `net_id` et univers, rejette les paquets invalides, réassemble en mode fragmenté. |
| EF-05  | Le nœud émet en continu une trame DMX512 sur UART1, TX = GPIO4, rafraîchie à ≥ 44 Hz, émission déclenchée à l'arrivée de données nouvelles. |
| EF-06  | Sur perte de flux, le nœud conserve la dernière trame ; blackout optionnel après `loss_blackout_ms` (défaut désactivé). Le relais n'est jamais affecté par la perte de flux. |
| EF-07  | Au démarrage, le nœud détecte sa variante par BOARD_SENSE (GPIO1 à la masse = partie rubans présente). |
| EF-08  | Relais (GPIO5) commandé par le canal DMX `start_address` (≥ 128 = allumé), par commande ESP-NOW (forçage / automatique) et en maintenance ; intervalle minimal entre commutations (défaut 3 s) ; état à la mise sous tension configurable (défaut : dernier état). |
| EF-09  | Variante rubans : 4 sorties PWM LEDC ≥ 4 kHz, ≥ 12 bits, gamma configurable, 8 ou 16 bits DMX par canal, PWM forcé à 0 avant toute autre action au démarrage, fondu configurable à l'allumage. |
| EF-10  | Le nœud émet un HEARTBEAT périodique (PROTOCOL §5.1). |
| EF-11  | Configuration persistante (univers, adresse, nom, canal radio, etc.) modifiable par commande ESP-NOW (PROTOCOL §6.4). |
| EF-12  | Mode maintenance (commande ESP-NOW ou action locale au démarrage) : point d'accès Wi-Fi, page de configuration, mise à jour OTA, retour automatique en exploitation. |
| EF-13  | CLI Pi : liste des nœuds (nom, MAC, variante, univers, adresse, RSSI, pertes, relais, uptime, version), identification, changement d'univers/adresse/nom, relais, maintenance, configuration du dongle. Page web minimale optionnelle. |
| EF-14  | Identification d'un nœud monté et fermé sans démontage (PROTOCOL `IDENTIFY`). |

### 2.2 Non fonctionnelles

| ID     | Exigence | Vérification |
|--------|----------|--------------|
| ENF-01 | Latence Art-Net → début d'émission des canaux du projecteur sur la ligne DMX < 10 ms (typique), mesurée hors quantification interne de QLC+. | Calcul §5.1 ; mesure à l'analyseur logique (GPIO de marquage dongle + ligne DMX). |
| ENF-02 | Rafraîchissement DMX ≥ 44 Hz, pas de trou > 100 ms en conditions nominales. | Mesure, compteur `lost_frames`. |
| ENF-03 | Taux de perte radio < 1 % à 20 m en vue directe, 4 univers actifs. | Mesure heartbeat. |
| ENF-04 | Coût matière ≤ 50 € par nœud en série de 20 (hors alimentation LED, hors XLR si fournie). | BOM chiffrée §6. |
| ENF-05 | Boîtier ≤ 150 × 65 × 45 mm (carte entière), ≤ 110 × 65 × 45 mm (cassée). Objectif, à confirmer après placement. | STEP. |
| ENF-06 | Nœud configurable, identifiable et mis à jour sans ouverture du boîtier. | Recette. |
| ENF-07 | Reproductibilité : tout est généré par scripts versionnés ; CI verte. | CI. |

### 2.3 Sécurité 🔴 RELECTURE HUMAINE OBLIGATOIRE

| ID     | Exigence |
|--------|----------|
| ES-01  | Isolation renforcée entre tout conducteur 230 V et la basse tension accessible (DMX, rubans, programmation) : lignes de fuite ≥ 6 mm, distances dans l'air ≥ 6 mm sur la carte (objectif de conception supérieur au minimum normatif, §4.8.2). |
| ES-02  | Alimentation interne isolée (PS1). Aucune liaison galvanique entre secteur et masse DMX. |
| ES-03  | Continuité du PE de J1 à J4 (et J4b), sans interruption par le relais. |
| ES-04  | Branche d'alimentation interne protégée par F1 (T500 mA) et RV1. Chemin de puissance protégé par le disjoncteur amont : dimensionnement du cuivre en conséquence (arbitrage A2). |
| ES-05  | Boîtier en matériau au moins UL94 V-1 (V-0 recommandé), borniers 230 V accessibles uniquement après retrait d'un couvercle vissé (outil requis), cloison entre zones, arrêts de traction sur tous les câbles secteur. |
| ES-06  | Aucun 230 V ne traverse ni n'approche à moins de 4 mm la ligne de découpe. |
| ES-07  | Aucune programmation ni mesure avec le secteur raccordé (procédure documentée), sauf équipement de test isolé explicitement prévu. |
| ES-08  | Toute la partie rubans est TBTS (< 60 V DC) et alimentée par une alimentation certifiée à sortie isolée. |

---

## 3. Architecture

### 3.1 Système

```
┌──────────── Raspberry Pi ────────────┐        ┌── dongle XIAO ESP32-C3 ──┐
│ QLC+ ──Art-Net──▶ 127.0.0.1:6454     │  USB   │ COBS/CRC ─▶ file d'émission│  ESP-NOW broadcast
│            dmxnowd (asyncio) ────────┼───────▶│ univers + commandes ──────┼──────────────▶ nœuds
│  CLI ◀── socket Unix ──┘             │◀───────┤ heartbeats / ACK ◀────────┼◀── unicast ── nœuds
└──────────────────────────────────────┘        └───────────────────────────┘
```

### 3.2 Nœud

```
Secteur ─▶ J1 ─┬─ L_IN ─▶ K1 (NO) ─▶ L_SW ─▶ J4 / J4b ─▶ projecteur + alim LED externe
               ├─ F1 ─▶ RV1 ─▶ PS1 (IRM-05-5, isolé) ─▶ +5V ─▶ U3 (AP2112K) ─▶ +3V3
               └─ PE, N ───────────────────────────────▶ J4 / J4b
+3V3 ─▶ U1 ESP32-C3-MINI-1
U1 IO4 ─▶ U2 SP3485 ─▶ D1 SM712 ─▶ J2 ─▶ queue XLR ─▶ entrée DMX du projecteur
U1 IO5 ─▶ Q1 AO3400 ─▶ bobine K1 (D2 roue libre)
───────────── ligne V-cut (BOARD_SENSE, PWM1-4, +5V, GND seulement) ─────────────
J5 12/24 V ─▶ F2 20 A ─▶ D3, C7, C8 ─▶ VLED ─▶ J6-VLED ─▶ rubans ─▶ J6-CH1..4 ─▶ Q2..Q5 ─▶ GND_LED
U1 IO6/7/10/3 ─▶ U4 74AHCT125 (5 V) ─▶ R7..R10 ─▶ grilles Q2..Q5
```

### 3.3 Répartition du code

| Composant          | Langage / cadre | Contenu |
|--------------------|-----------------|---------|
| `firmware/common`  | C++17, sans dépendance Arduino | En-tête, CRC16, COBS, codec TLV, réassemblage, anti-rebond relais, table gamma, compteur de pertes. Testé nativement (`pio test -e native`). |
| `firmware/node`    | PlatformIO, Arduino-ESP32 3.x (pioarduino) | Tâches radio, DMX, contrôle, maintenance. |
| `firmware/dongle`  | idem | Série USB, ordonnanceur d'émission, suivi des commandes. |
| `pi/`              | Python ≥ 3.11, asyncio, `pyserial` | Démon `dmxnowd`, CLI `dmxnow`, systemd, udev, installeur. |
| `hardware/`        | Python (SKiDL + génération `.kicad_pcb` scriptée), `kicad-cli` | Schéma, placement, routage, ERC/DRC, sorties JLCPCB. |
| `enclosure/`       | CadQuery | Boîtier paramétrique deux longueurs. |

---

## 4. Choix techniques justifiés

### 4.1 Radio (ADR 0001, 0011)

ESP-NOW v2, un paquet par univers, broadcast, canal fixe, débit PHY 6 Mbit/s par défaut.
Voir PROTOCOL §2 et le calcul §5.

Mode Wi-Fi des nœuds : STA non associée, `WIFI_PS_NONE` (l'économie d'énergie
introduirait des latences de l'ordre de l'intervalle de balise, 100 ms). Protocoles
802.11b/g/n activés.

**Repli sur changement de canal [ARBITRAGE A5 — retenu]** : un nœud qui ne reçoit plus
aucun paquet de son réseau depuis 60 s balaie les canaux 1 à 13 (écoute 300 ms par canal)
jusqu'à retrouver son `net_id` (DMX_DATA ou BEACON), puis adopte ce canal et le persiste.
La dernière trame DMX continue d'être émise pendant le balayage. Évite qu'un nœud reste
orphelin après un changement de canal manqué. Aucun coût matériel.

### 4.2 Microcontrôleur et affectation des broches (ADR 0003)

ESP32-C3-MINI-1 (flash intégrée 4 Mo, antenne PCB intégrée). GPIO11 à GPIO17 sont réservés
à la flash interne ; GPIO2, GPIO8 et GPIO9 sont des broches de configuration de démarrage
(*strapping*) [V-HW-02].

| GPIO   | Fonction          | Remarques |
|--------|-------------------|-----------|
| IO0    | STATUS_LED (option) | R19 1 kΩ en série, D4 LED CMS 0603 vers GND ; composants à monter en option [ARBITRAGE A7 — option], §4.9 |
| IO1    | BOARD_SENSE       | Entrée, pull-up interne ; GND sur la partie rubans |
| IO2    | libre (strapping) | R4 10 kΩ pull-up, doit être haut au démarrage |
| IO3    | PWM4              | via U4 |
| IO4    | DMX_TX            | UART1 TX vers SP3485 DI |
| IO5    | RELAY_CTRL        | R5 vers grille Q1, R6 pull-down |
| IO6    | PWM1              | via U4 |
| IO7    | PWM2              | via U4 |
| IO8    | libre (strapping) | R3 10 kΩ pull-up, doit être haut pour le mode téléchargement |
| IO9    | BOOT              | R2 pull-up, pastille J3-BOOT |
| IO10   | PWM3              | via U4 |
| IO18/19| USB D−/D+         | J3 |
| IO20/21| UART0             | non connectés (console via USB CDC) |

Point important : **GPIO9 à la masse pendant le reset fait entrer l'ESP32-C3 dans le
chargeur ROM (mode téléchargement), pas dans notre firmware.** La demande « BOOT à la
masse au démarrage ⇒ maintenance » est donc reformulée : maintenance si BOOT est maintenu
à la masse ≥ 3 s **après** le démarrage de l'application (fenêtre des 10 premières
secondes), ou à tout moment ≥ 5 s. Entrée sans ouverture du boîtier : 3 mises sous
tension rapprochées, activable par configuration [ARBITRAGE A6 — option], §4.9.

### 4.3 Alimentation basse tension et budget 🔴 RELECTURE HUMAINE OBLIGATOIRE (partie PS1)

PS1 **Mean Well IRM-05-5** : 85 à 264 V AC → 5 V, 1 A (5 W), homologué IEC/EN/UL 62368-1
selon le fabricant [V-HW-09], environ 8 € **[ARBITRAGE A1 — retenu, amende la décision 4]**.
Raison : les modules Hi-Link (HLK-PM05, décision initiale) ont des certifications
difficiles à vérifier et sont souvent contrefaits ; pour un boîtier publié et refabriqué
par d'autres, un module certifié réduit le risque d'isolement (R-03). Principe inchangé
(module isolé, 2 broches AC, 2 broches DC) ; F1 et RV1 conservés sous réserve des
recommandations de la fiche Mean Well. Le HLK-PM05 reste une empreinte de repli
paramétrable dans le script de placement [V-HW-01], non retenue par défaut.

Budget sur +5 V (valeurs à confirmer en datasheet) :

| Consommateur                          | Moyen   | Crête   | Source |
|---------------------------------------|---------|---------|--------|
| ESP32-C3 en réception continue + CPU 160 MHz (via U3) | ~100 mA | — | [V-HW-02] |
| ESP32-C3 en émission 802.11g ~15 dBm (heartbeats, brefs) | — | ~300 mA | [V-HW-02] |
| SP3485 pilotant une ligne terminée 120 Ω (via U3) | ~20 mA | ~35 mA (2 terminaisons) | [V-HW-06] |
| Bobine K1 5 V (≈ 400 mW)              | ~80 mA  | ~80 mA  | [V-HW-03] |
| U4 + charges de grille (4 × Qg × fPWM) | < 2 mA | —       | — |
| **Total**                             | **~200 mA** | **~420 mA** | ≤ 1 A (IRM-05-5) : marge > 50 % en crête |

Régulateur U3 AP2112K-3.3 (600 mA, faible chute) : dissipation moyenne
(5 − 3,3) V × ~120 mA ≈ 0,2 W. En SOT-23-5 (RθJA de l'ordre de 150 à 250 °C/W selon le
cuivre), l'échauffement est de 30 à 50 °C : **acceptable seulement avec une surface de
cuivre 2 oz généreuse sur les broches GND/VOUT** et à vérifier par mesure (R-07).

### 4.4 Sortie DMX

- SP3485 alimenté en 3,3 V, DE et /RE à 3V3 : émetteur actif en permanence, récepteur
  désactivé (RO non connecté). Pas de polarisation (*fail-safe*) nécessaire puisque la
  ligne est toujours pilotée.
- D1 SM712 : TVS asymétrique −7 V / +12 V adaptée à la plage de mode commun RS-485.
- **Pas de terminaison 120 Ω sur le nœud** : le nœud est l'émetteur, en tête de ligne ;
  la terminaison appartient à l'extrémité (bouchon sur la sortie THRU du projecteur si
  l'utilisateur chaîne, sinon inutile sur une queue de ≤ 1 m à 250 kbit/s, où le temps de
  propagation, ~5 ns, est négligeable devant le temps de bit, 4 µs).
- Masse DMX (J2-1) = GND du nœud, isolée du secteur par PS1. Côté projecteur, la broche 1
  est souvent reliée au châssis donc au PE : la masse du nœud se retrouve référencée au PE
  par le projecteur, ce qui est normal (un seul point de référence). Voir R-09 pour la
  boucle possible avec la masse des rubans.
- Pilote : bibliothèque `esp_dmx` (someweisguy) sur UART1, TX GPIO4. Compatibilité
  annoncée « ESP-IDF ≥ 4.4.1, Arduino-ESP32 ≥ 2.0.3 » ; la compatibilité avec
  Arduino 3.x / IDF 5.5 n'est pas explicitement annoncée [V-FW-03]. Repli : pilote
  UART maison (le DMX en émission seule est simple : break par
  `uart_write_bytes_with_break()` ou par inversion de ligne, MAB, 513 octets à 250 kbit/s,
  8N2), ~150 lignes, testable. La fonction `dmx_send_num()` d'esp_dmx permet l'émission
  de trames courtes.
- **Trames courtes [ARBITRAGE A3]** : voir §5.1 ; paramètre `dmx_out_slots`.

### 4.5 Relais 🔴 RELECTURE HUMAINE OBLIGATOIRE (partie contacts)

K1 Omron G5RL-U1A-E, bobine 5 V DC, contact NO 16 A, conçu pour courants d'appel élevés
(« 16-A High Inrush Switching », ligne de fuite bobine-contacts 8 mm, tenue aux chocs de
10 kV selon la fiche Omron K265-E1 [V-HW-03]). Q1 AO3400 (VGS(th) max 1,45 V, commandable
en 3,3 V), R5 100 Ω limite le courant de grille et amortit, R6 100 kΩ maintient Q1 bloqué
pendant le démarrage. D2 1N4148W en roue libre : la roue libre par simple diode ralentit
l'ouverture du contact (quelques ms) — acceptable ici et même favorable (pas de rebond) ;
à confirmer que la vitesse d'ouverture n'aggrave pas l'érosion à la coupure de charges
capacitives (charges LED : l'usure se fait surtout à la fermeture, sur l'appel de courant).

Logique (implémentée dans `common`, testée) :
1. `desired` = état demandé par la source prioritaire : forçage par commande
   (`RELAY` 0/1) > canal DMX (si `relay_dmx` = 1 et flux présent) > état au démarrage.
   `RELAY 2` lève le forçage. Le forçage n'est pas persistant (perdu au redémarrage).
2. Le canal DMX agit sur **niveau** (≥ 128 allumé, < 128 éteint), pas sur front.
3. Anti-rebond : si `desired` ≠ état réel et que la dernière commutation date de moins de
   `relay_min_interval_ms`, la commutation est **différée** (pas ignorée) jusqu'à
   l'échéance ; c'est alors la dernière valeur de `desired` qui s'applique. Un
   clignotement DMX rapide produit donc au plus une commutation toutes les 3 s.
4. Perte de flux : le relais conserve son état (EF-06).
5. Persistance du dernier état : écriture NVS **uniquement** lors d'une commutation
   effective, regroupée avec `relay_switch_count`. Avec l'intervalle minimal de 3 s, le pire
   cas pathologique est de 1200 écritures/h ; la NVS répartit l'usure sur ses pages
   (partition 20 Ko = 5 pages de 126 entrées de 32 octets, ~100 000 cycles
   d'effacement par secteur) : plusieurs dizaines de millions d'écritures, soit des
   années même dans ce pire cas. Usage réel : quelques commutations par jour.

### 4.6 Sortie rubans (partie sécable)

- 4 MOSFET N côté masse AOD4184A (40 V ; RDS(on) de l'ordre de 7 mΩ à VGS 10 V et 10 mΩ à
  4,5 V [V-HW-07]). Commande en 5 V par U4 74AHCT125 (entrées compatibles TTL, VIH 2 V,
  donc attaquables en 3,3 V ; sortie 5 V pour une meilleure saturation que 3,3 V).
  R15-R18 100 kΩ maintiennent les entrées de U4 à 0 pendant le démarrage ; /OE à GND.
- Courant : 200 W sous 12 V = 16,7 A total, soit ~4,2 A par canal en RGBW équilibré ;
  on dimensionne chaque canal pour **6 A** et le total pour 17 A (F2 20 A).
- Pertes par MOSFET à 4,2 A : conduction I²R ≈ 4,2² × 0,010 ≈ 0,18 W ; commutation à
  4,9 kHz ≈ 0,05 à 0,1 W (temps de transition ~150 à 200 ns avec 100 Ω de grille et un
  étage AHCT) ; total ≈ 0,25 W par MOSFET, ~1 W pour les quatre. En DPAK sur ~2 cm² de
  cuivre 2 oz (RθJA ≈ 50 °C/W) : ΔT ≈ 15 °C. Aérations prévues au boîtier.
- **Ondulation dans C7** : les 4 canaux commutent jusqu'à 17 A en créneaux ; le courant
  alternatif absorbé par C7 peut dépasser plusieurs ampères efficaces, bien au-delà du
  courant d'ondulation admissible d'un 470 µF 35 V courant (~1 A). Mesures : (a) C7
  faible ESR, 105 °C, courant d'ondulation ≥ 2 A à 100 kHz [V-HW-08] ; (b) **déphasage
  des 4 PWM** (paramètre `hpoint` du LEDC décalé d'un quart de période par canal),
  sans coût matériel, qui étale les appels de courant et réduit fortement l'ondulation
  d'entrée. Justifié comme exigence firmware (EF-09).
- D3 SMBJ28A : tension de veille 28 V (compatible 24 V + 10 %), tension d'écrêtage
  ≈ 45 V à Ipp : **supérieure aux 40 V des MOSFET**. Une surtension sur VLED passe donc
  en partie sur les MOSFET bloqués. Risque R-10, à arbitrer lors du livrable PCB
  (option : MOSFET 60 V de même boîtier).
- Chemin VLED, retour GND_LED : 17 A, largeur de piste §4.8.3 ; F2, C7 et D3 collés à J5 ;
  retour de courant des rubans (J6 → MOSFET → GND_LED → J5) entièrement dans la partie
  sécable.
- Borniers 17 A : WAGO 2604 annoncé 32 A / 320 V (IEC) [V-HW-04], largement suffisant.

### 4.7 PWM (firmware)

- LEDC de l'ESP32-C3 (horloge APB 80 MHz) : résolution maximale = log2(80 MHz / f).
  Défaut **4882 Hz en 14 bits** (80 MHz / 2¹⁴) ; à 19,5 kHz, 12 bits. La fréquence est
  configurable (`pwm_freq_hz`), la résolution déduite (≥ 12 bits imposé ⇒ f ≤ 19,5 kHz).
- Gamma : table précalculée à la configuration. 8 bits : 256 entrées → valeur 14 bits ;
  16 bits : 257 points + interpolation linéaire. `gamma_x10` = 10 donne une courbe linéaire.
- Démarrage : premières instructions du firmware = configurer les 4 broches PWM en sortie
  à 0 (si variante rubans), avant Wi-Fi, NVS ou DMX.
- Fondu `fade_on_ms` : appliqué au démarrage et à chaque passage du relais à « allumé »
  (l'alimentation LED externe redémarre), rampe linéaire en perception (sur la valeur
  avant gamma).
- Déphasage des 4 canaux (§4.6).

### 4.8 PCB 🔴 RELECTURE HUMAINE OBLIGATOIRE (zone 230 V, isolement, largeurs)

#### 4.8.1 Généralités

2 couches, FR-4 TG ≥ 150, cuivre 2 oz (70 µm) sur les deux faces, épaisseur 1,6 mm,
~130 × 50 mm entière, V-cut vertical à ~90 mm. Dimensions finales après placement : la
ligne de 3 borniers 3 pôles (J1, J4, J4b) au pas de 5 mm impose ~50 mm de bord, PS1
(~34 × 20 mm) et K1 (~33 × 13 mm) occupent l'essentiel de la zone 230 V ; la hauteur de 50 mm
est tenable mais serrée [V-HW-10].

Zonage (vue de dessus, schématique) :

```
┌──────────── partie principale ~90 mm ──────────────┬4mm┊4mm┬── partie rubans ~40 mm ──┐
│ J1  J4  J4b  │ fente │ PS1 DC │ U3 │ U1 ESP32 [ant.]│    ┊   │ J5 F2 C7 D3  Q2..Q5 J6    │
│ F1 RV1 K1-contacts│ 1 mm │ K1-bobine Q1 D2 │ U2 D1 J2 │   ┊   │ U4 R7..R18                │
│   ZONE 230 V  ←≥ 6 mm→   ZONE BASSE TENSION        │ V-cut ┊                           │
└────────────────────────────────────────────────────┴───────┴───────────────────────────┘
```

L'antenne de U1 est placée en bord de carte, côté opposé à la zone 230 V et éloignée des
MOSFET, avec zone d'exclusion cuivre sur les deux couches (dimensions selon le guide de
conception matérielle Espressif [V-HW-02]).

#### 4.8.2 Isolement

- Isolation renforcée secteur ↔ TBT (IEC 62368-1, tension de service 250 V eff., catégorie
  de surtension II, degré de pollution 2, FR-4 groupe de matériau IIIb) : ligne de fuite
  minimale **5,0 mm** (2 × 2,5 mm de l'isolation principale), distance dans l'air
  minimale de l'ordre de **3 à 4 mm** selon la tension transitoire retenue [V-HW-11].
  **Objectif retenu : 6 mm pour les deux**, avec fente fraisée de 1 mm sous PS1 entre broches
  AC et DC, prolongée entre contacts et bobine de K1. Une fente ≥ 1 mm de large compte
  comme interruption de la ligne de fuite en degré de pollution 2 (la ligne de fuite contourne
  la fente).
- Entre conducteurs 230 V de polarité différente (L, N, L_SW) : isolation fonctionnelle,
  objectif ≥ 3 mm (le pas de 5 mm des borniers le permet).
- Entre L_IN et L_SW (contact ouvert du relais) : objectif ≥ 3 mm hors relais.
- Aucun plan de masse, aucune piste TBT, aucun via TBT dans la zone 230 V, sur aucune couche.
- Les distances seront vérifiées par règles DRC par classe de réseaux (`netclass` MAINS vs
  LV : clearance 6 mm) et par un contrôle scripté de ligne de fuite simplifié.

#### 4.8.3 Chemins de puissance secteur — **[ARBITRAGE A2 — cuivre 16 A retenu]**

Le chemin de charge (J1 → K1 → J4) n'a **aucun fusible sur la carte** (F1 ne protège que
PS1). Il est donc protégé uniquement par le disjoncteur amont, typiquement **16 A** en
France. Une carte dimensionnée pour 10 A pourrait être surchargée durablement entre 10 et
16 A sans déclenchement. Décision : **dimensionner le cuivre du chemin de charge pour
16 A** (le relais et les borniers le sont), charge nominale déclarée de 10 A marquée sur
le boîtier, pas de fusible de charge sur la carte.

Calcul (IPC-2221, couche externe, `I = 0,048 × ΔT^0,44 × A^0,725`, A en mil²) — formule
conservatrice ; à recouper avec les abaques IPC-2152 (par ex. Saturn PCB Toolkit) :

| Courant | ΔT    | Section requise | Largeur en 2 oz (2,8 mil) |
|---------|-------|-----------------|---------------------------|
| 10 A    | 20 °C | 256 mil²        | 2,3 mm |
| 10 A    | 10 °C | 390 mil²        | 3,5 mm |
| 16 A    | 20 °C | 490 mil²        | 4,5 mm |
| 17 A (VLED) | 20 °C | 532 mil²    | 4,8 mm |

Règle de conception proposée : pistes de puissance **≥ 5 mm sur les deux faces en
parallèle**, reliées par une rangée de vias (ou recouvertes d'étain par ouverture du vernis),
longueurs minimisées (< 30 mm). Résistance d'une piste 5 mm × 70 µm × 30 mm ≈ 1,5 mΩ par
face. Pertes à 10 A dans le cuivre, les contacts du relais et 6 bornes : ~1,5 à 2,5 W au
total (dominé par le contact du relais) — à prendre en compte dans le boîtier (R-08) ;
elles tombent sous 0,1 W pour une charge réaliste de 1 à 2 A. Alternative mentionnée par le
cahier des charges : fils soudés sur les broches du relais, retenue seulement si le
placement ne permet pas les largeurs.

#### 4.8.4 Ligne de découpe

- Traversent la découpe : PWM1-4, BOARD_SENSE, +5V, GND uniquement (TBT).
- 4 mm sans composant de chaque côté ; cuivre à ≥ 0,5 mm de l'axe du V-cut [V-HW-12].
- La GND qui traverse n'est qu'une référence (pistes fines, ~0,5 mm) : le courant des
  rubans ne doit pas pouvoir y circuler en fonctionnement normal. Cf. R-09.

#### 4.8.5 Méthode de production

Schéma saisi par script (SKiDL) → netlist ; génération du `.kicad_pcb` par script
(placement coordonné, contour, fentes, V-cut sur calque `Edge.Cuts`/`User.Comments` selon
les règles JLCPCB, zones, classes de réseaux) ; routage des pistes de puissance et de
l'isolement **scripté** (trop critique pour un autorouteur), routage signal par Freerouting
(DSN/SES) ; ERC et DRC par `kicad-cli` ; sorties Gerber, perçage, BOM et CPL au format
JLCPCB, rendus 3D PNG. Document `hardware/REVIEW.md` : liste des points de contrôle
pour la relecture humaine.

### 4.9 Maintenance et OTA

- Entrée : commande `MAINTENANCE`, action BOOT (§4.2), ou **3 mises sous tension
  rapprochées [ARBITRAGE A6 — option]**, activée par la clé de configuration
  `powercycle_maint` (**activée par défaut**, désactivable par nœud ; un nœud dont la
  radio est perdue ne peut être reconfiguré que par cette voie ou en ouvrant le
  boîtier, d'où ce défaut). Principe : au démarrage, le nœud incrémente un compteur
  NVS et le remet à zéro après 5 s de fonctionnement ; si le compteur atteint 3 (trois
  démarrages espacés de moins de 5 s), il passe en maintenance. Usure NVS : 2 écritures
  par démarrage, négligeable. Le relais applique son état au démarrage normalement : la
  manœuvre coupe et rétablit aussi le projecteur, à documenter. Permet de récupérer un
  nœud dont le canal ou le `net_id` est inconnu sans ouvrir le boîtier. Désactivée, le
  compteur n'est ni lu ni écrit.
- **LED d'état [ARBITRAGE A7 — option]** : l'empreinte D4 (LED CMS 0603) + R19 (1 kΩ,
  ~1 mA sous 3,3 V, suffisant pour un guide de lumière) est **toujours présente** sur le
  PCB, câblée sur IO0 (broche libre, sans rôle de strapping sur l'ESP32-C3). Les deux
  composants sont **non montés par défaut** (DNP) ; la génération des sorties produit deux
  BOM JLCPCB : `bom_base` et `bom_led`. Côté firmware, la clé `status_led` (défaut 0)
  active la LED : allumée fixe = flux DMX présent ; clignotement lent (1 Hz) = réseau
  présent sans flux sur son univers ; double éclat = aucun réseau (balayage) ; clignotement
  rapide (5 Hz) = maintenance ; pendant `IDENTIFY`, la LED clignote avec le reste. Côté
  boîtier, le paramètre `light_pipe` (défaut `False`) ajoute un logement de guide de lumière
  (Ø 3 mm) au droit de D4. Coût de l'option : < 0,1 € + guide de lumière.
- Point d'accès WPA2 `dmxnow-<nom>` sur **le même canal que le réseau ESP-NOW** : l'ESP32
  peut conserver la réception ESP-NOW en mode AP+STA sur le canal commun ; le DMX continue
  donc d'être rafraîchi en maintenance, au mieux [V-FW-05].
- Mot de passe : `maint_password` ; à défaut, mot de passe aléatoire de 12 caractères généré
  au premier démarrage, stocké en NVS, lisible uniquement par `GET_CONFIG` authentifiée
  (A4) ou par la console USB. (Un mot de passe dérivé de la MAC serait devinable.)
- Page web minimale (configuration, état, téléversement du firmware), OTA par partitions
  `ota_0`/`ota_1` (2 × 1,9 Mo sur 4 Mo) ; validation de l'image (retour arrière si le
  nouveau firmware ne reçoit pas de paquet valide dans les 60 s) si le chargeur d'amorçage
  Arduino 3.x le permet [V-FW-06].
- Sortie : après OTA réussie (redémarrage), sur bouton de la page, ou après `timeout_s`
  (défaut 600 s) sans client connecté.

### 4.10 Dongle

- XIAO ESP32-C3 alimenté par l'USB du Pi. Antenne externe du XIAO (connecteur U.FL) :
  l'antenne fournie doit être montée ; placer le dongle en hauteur (rallonge USB) plutôt
  que derrière le Pi.
- Ordonnanceur : file prioritaire (COMMAND > DMX_DATA > BEACON), émission ESP-NOW
  séquentielle (attente du callback d'émission avant l'envoi suivant, pour ne pas saturer
  la file interne).
- Mesure : une broche GPIO du dongle bascule à chaque émission (point de mesure de latence
  pour ENF-01, sans coût).

### 4.11 Démon Raspberry Pi

- Python ≥ 3.11 (Raspberry Pi OS Bookworm), asyncio, dépendances minimales : `pyserial`
  (lecture/écriture dans un thread dédié relié à asyncio), bibliothèque standard pour le
  reste (argparse, json, hmac). Page web optionnelle : `aiohttp` en extra optionnel.
- Art-Net : ArtDmx (OpCode 0x5000), ArtPoll (0x2000) → ArtPollReply (0x2100) annonçant
  les univers configurés (4 ports par réponse, plusieurs `BindIndex` si > 4 univers). sACN
  optionnel (UDP 5568, multicast `239.255.hi.lo`).
- Configuration `/etc/dmxnow/dmxnowd.toml` : univers transmis, interfaces d'écoute,
  paramètres radio du dongle, clé réseau (A4), compteur d'authentification dans
  `/var/lib/dmxnow/`.
- CLI `dmxnow` ↔ démon par socket Unix `/run/dmxnow/control.sock` (JSON ligne par ligne).
- udev : `SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="1001",
  ATTRS{serial}=="<MAC du dongle>", SYMLINK+="dmx-dongle"`. Le couple VID:PID est commun à
  tous les ESP32-C3/S3 en USB natif, d'où le filtrage par numéro de série (l'installeur le
  détecte). systemd : `Restart=always`, `RestartSec=1`, utilisateur dédié membre de
  `dialout`.
- Installation : `pi/install.sh` (venv dans `/opt/dmxnow`, service, règle udev), idempotent.

### 4.12 Boîtier 🔴 RELECTURE HUMAINE OBLIGATOIRE (cloison, accès bornes, matériau)

- Modèle CadQuery unique, paramètre `variant = "full" | "cut"`, dimensions intérieures
  dérivées du STEP exporté du PCB + 0,5 mm de jeu.
- Fond + couvercle principal (côté basse tension, vissé M3 sur inserts à chaud) +
  couvercle d'accès borniers 230 V séparé, vissé (outil requis), permettant d'actionner
  les leviers WAGO.
- Cloison intérieure solidaire du fond entre zones 230 V et TBT, alignée sur la fente
  du PCB, hauteur jusqu'au couvercle (recouvrement par une lèvre).
- Entrées de câbles :
  - secteur entrée, sortie projecteur, sortie alimentation LED : presse-étoupes M16 ou PG9
    selon le diamètre des cordons H05VV-F 3G1,5 (≈ 8 à 9 mm) [V-ENC-01] **plus** étrier
    de serrage imprimé vissé (arrêt de traction indépendant du presse-étoupe) ;
  - queue DMX : PG7 (plage 3 à 6,5 mm) — les câbles DMX 120 Ω font souvent 6 à 6,5 mm :
    à vérifier, sinon M12 [V-ENC-01] ;
  - version entière : entrée 12/24 V et sortie rubans, presse-étoupes PG7/PG9.
- Rien de métallique devant l'antenne (inserts et vis hors d'une zone de 15 mm autour).
- Version entière : fentes d'aération au-dessus des MOSFET, ou fenêtre + pad thermique vers
  une paroi (à choisir au livrable boîtier).
- Passants pour colliers de serrage (largeur 5 à 8 mm) sur le fond.
- Parois ≥ 2,0 mm (2,5 mm sur les faces portant des presse-étoupes), impression sans
  support : fond et couvercles imprimés face plane sur le plateau, trous de presse-étoupes
  en « goutte d'eau » si horizontaux.
- **Matériau** : il faut un matériau au moins UL94 V-1 pour une enveloppe contenant des
  circuits secteur (enveloppe coupe-feu au sens d'IEC 62368-1) ; le PETG et l'ABS standard
  sont classés HB et ne conviennent pas. Recommandation : **PC-ABS ou ABS ignifugé V-0**
  (ex. famille « ABS-FR / PC-ABS-FR » chez plusieurs fabricants) ou **PC-FR** (plus
  résistant en température, plus difficile à imprimer). Mon choix par défaut : **ABS-FR
  V-0**, imprimable sur une imprimante fermée standard (buse 240 à 260 °C, plateau 100 °C),
  bonne tenue en température (Tg ~100 °C) près du relais et des MOSFET. Réserves : la
  classification V-0 porte sur le matériau à une épaisseur donnée (souvent 1,5 ou 3 mm) ;
  la pièce imprimée doit avoir des parois pleines (100 % de remplissage des parois
  ≥ épaisseur certifiée) ; fiche technique du filament à conserver [V-ENC-02].
- Option `light_pipe` (A7) : logement de guide de lumière Ø 3 mm au droit de D4, dans le
  couvercle basse tension.
- Exports : STL et STEP pour chaque pièce et chaque variante (avec et sans `light_pipe`),
  rendu PNG assemblé.

---

## 5. Budgets de latence et de débit

### 5.1 Latence Art-Net → ligne DMX

Hypothèses : 1 univers de 512 canaux, radio v2 à 6 Mbit/s, dongle et nœud en émission
sur événement (PROTOCOL §4.4).

Temps d'antenne d'un DMX_DATA : 530 octets utiles + ~60 octets d'encapsulation
(en-tête MAC 24, catégorie/OUI/aléa 8, éléments vendeur ~20, FCS 4 ; valeur exacte v2 à
confirmer [V-FW-07]) ≈ 590 octets = 4720 bits → 0,79 ms à 6 Mbit/s + préambule 20 µs +
DIFS 28 µs + attente aléatoire moyenne ~70 µs ≈ **0,9 ms** (≈ 5 ms à 1 Mbit/s DSSS).

Durée d'une trame DMX de N canaux : break 176 µs + MAB 12 µs + (N + 1) × 44 µs.
N = 512 → **22,7 ms** ; N = 40 → 2,0 ms.

| Étape                                           | Typique | Pire cas | Commentaire |
|-------------------------------------------------|---------|----------|-------------|
| QLC+ → UDP loopback → démon                     | 0,2 ms  | 1 ms     | hors cadence interne QLC+ (50 Hz, 20 ms) |
| Démon : parsing, encodage COBS, écriture        | 0,3 ms  | 2 ms     | Python ; pire cas = ordonnancement Linux |
| USB CDC (≈ 540 octets)                          | 0,5 ms  | 2 ms     | trames USB de 1 ms, paquets bulk de 64 o [V-FW-04] |
| Dongle : décodage, CRC, `esp_now_send`          | 0,1 ms  | 0,5 ms   | |
| Radio (6 Mbit/s)                                | 0,9 ms  | 3 ms     | pire cas : canal occupé par un Wi-Fi voisin |
| Nœud : callback → tâche DMX                     | 0,1 ms  | 0,5 ms   | |
| Attente de fin de la trame DMX en cours, N = 512 | 11 ms  | 22,7 ms  | émission non interruptible |
| Attente de fin de la trame DMX en cours, N = 40  | 1 ms   | 2,0 ms   | |
| Émission jusqu'au canal k (k petit)             | 0,2 ms  | 0,2 + 0,044 × k ms | |
| **Total, trame DMX 512 canaux**                 | **~13 ms** | **~34 ms** | objectif < 10 ms **non tenu** |
| **Total, trame DMX 40 canaux**                  | **~3,3 ms** | **~13 ms** | objectif tenu en typique |

De plus, beaucoup de projecteurs n'appliquent les valeurs qu'en fin de trame (au break
suivant), ce qui ajoute une durée de trame complète : encore un argument pour les trames
courtes.

**[ARBITRAGE A3 — défaut 512 retenu]** : l'objectif < 10 ms n'est tenable qu'avec des trames DMX courtes
(n'émettre que jusqu'au dernier canal utile du projecteur). Le DMX512 l'autorise (trames de
24 à 512 canaux ; intervalle break à break ≥ 1204 µs, respecté dès 24 canaux). Certains
appareils anciens supportent mal les trames courtes. Proposition : paramètre
`dmx_out_slots` par nœud, **défaut 512** (compatibilité maximale), réglé par la CLI à la
mise en service à « adresse de fin du projecteur », avec recommandation documentée. La
CLI affichera un avertissement pour tout nœud resté à 512. ENF-01 est donc vérifiée sur un
nœud configuré en trame courte.

### 5.2 Débit et occupation radio

| Grandeur                                    | Valeur |
|---------------------------------------------|--------|
| Débit utile par univers à 44 Hz             | 44 × 530 o ≈ 23 ko/s |
| Occupation du canal par univers à 44 Hz, 6 Mbit/s | 44 × 0,9 ms ≈ **4 %** |
| Idem à 50 Hz (cadence QLC+)                 | ≈ 4,5 % |
| Idem à 1 Mbit/s                             | ≈ 22 % |
| Mode fragmenté v1, 3 paquets, 6 Mbit/s      | ≈ 1,6 ms/univers, ≈ 7 % |
| HEARTBEAT, 30 nœuds, 0,5 Hz, ~74 o          | < 0,5 % |
| BEACON                                      | < 0,1 % |

Limite recommandée : **4 univers par dongle et par canal** (≈ 18 % d'occupation à
6 Mbit/s), pour laisser de la marge aux réseaux Wi-Fi voisins et aux retransmissions. Le
protocole n'impose pas de limite (15 bits d'univers). Le nombre de nœuds n'est pas limité
par le broadcast (un nœud écoute sans coût radio) ; il l'est seulement par le trafic de
heartbeats (plusieurs centaines de nœuds avant 5 %).

### 5.3 Fiabilité

Sans acquittement en broadcast, une trame perdue est corrigée par la suivante 22,7 ms
plus tard au pire (20 ms à la cadence QLC+). À 1 % de perte, la probabilité de 3 trames
consécutives perdues (~70 ms de gel, perceptible sur un effet rapide) est de 10⁻⁶ par
trame, soit environ une fois toutes les 6 heures par univers ; à 5 %, une fois par
10 secondes. D'où ENF-03 et le choix du canal comme premier levier.

---

## 6. Coût estimé par nœud (série de 20, prix indicatifs 2025-2026, à confirmer)

| Poste                                   | Carte entière | Carte cassée |
|-----------------------------------------|---------------|--------------|
| ESP32-C3-MINI-1                         | 2,5 €         | 2,5 € |
| Mean Well IRM-05-5 (A1)                 | 8 €           | 8 € |
| Omron G5RL-U1A-E                        | 2,5 €         | 2,5 € |
| WAGO 2604 : 3 × 3 pôles (+ 2 + 5 pôles) | 6 € (+ 4 €)   | 6 € |
| SP3485, SM712, AP2112K, AO3400, passifs | 1,5 €         | 1,5 € |
| Partie rubans : 4 × AOD4184A, 74AHCT125, porte-fusible ATO + fusible, C7, D3, passifs | 3,5 € | — |
| PCB 2 couches 2 oz + assemblage CMS JLCPCB (répartis) | 5 € | 5 € |
| Boîtier ABS-FR (~60 g) + inserts + vis  | 3 €           | 2,5 € |
| Presse-étoupes (4 à 6)                  | 2,5 €         | 1,5 € |
| Queue DMX : 1 m de câble 120 Ω + Neutrik NC3FXX | 5,5 € | 5,5 € |
| **Total**                               | **≈ 49 €**    | **≈ 37 €** |

Dans la cible de 30 à 50 €, mais la carte entière est en limite haute depuis le choix de l'IRM-05-5 (A1). Les postes les plus sensibles sont la connectique (WAGO, Neutrik) et PS1.
Les composants traversants (WAGO, relais, PS1, porte-fusible) ne sont probablement pas dans
la bibliothèque d'assemblage JLCPCB : soudure manuelle ou assemblage traversant payant
[V-HW-13].

---

## 7. Risques

| ID   | Risque | Impact | Probabilité | Mesure |
|------|--------|--------|-------------|--------|
| R-01 | 🔴 Défaut d'isolement secteur/TBT (placement, fabrication, humidité) | Électrocution via la XLR ou les rubans | Faible si règles appliquées | ES-01, fente, DRC par classes, relecture humaine, test diélectrique recommandé (§8.2) |
| R-02 | 🔴 Surcharge du chemin de charge entre 10 et 16 A | Échauffement, incendie | Moyenne sur installation mal dimensionnée | A2, marquage de la charge maximale sur le boîtier |
| R-03 | Contrefaçon ou certification douteuse de PS1 | Défaut d'isolement | Faible (IRM-05-5, A1) | Achat chez un distributeur agréé |
| R-04 | `esp_dmx` incompatible avec Arduino 3.x / IDF 5.5 | Retard firmware | Moyenne | Pilote DMX maison de repli (§4.4) |
| R-05 | Plateforme pioarduino abandonnée ou incompatible | Build cassé | Faible à moyenne | Versions épinglées dans `platformio.ini` ; repli ESP-IDF pur possible (le code `common` est indépendant d'Arduino) ; repli radio v1 fragmenté |
| R-06 | Latence > 10 ms avec trames DMX de 512 canaux | Objectif non tenu | Certaine avec N = 512 | A3 |
| R-07 | Échauffement de U3 (LDO) | Dérive, arrêt thermique | Moyenne | Cuivre, mesure ; repli : convertisseur abaisseur (nouvel arbitrage) |
| R-08 | Échauffement dans un boîtier fermé (relais 0,4 W, PS1 ~0,6 W, contacts à fort courant, MOSFET ~1 W) | Vieillissement, déformation du boîtier | Moyenne | Aérations, matériau Tg ≥ 100 °C, mesure à charge nominale |
| R-09 | Boucle de masse : GND_LED (alimentation LED) reliée à la GND DMX, elle-même souvent au PE via le projecteur ; si le −V de l'alimentation LED est aussi relié au PE, une partie du courant des rubans peut circuler par la masse DMX et la piste GND de la découpe | Perturbations DMX, échauffement d'une piste fine | Faible (Mean Well LRS/HLG : sortie flottante) | Documenter : sortie de l'alimentation LED non reliée à la terre ; option résistance/ferrite série dans la GND de découpe à évaluer au PCB |
| R-10 | Écrêtage de D3 (≈ 45 V) au-delà de VDS max des MOSFET (40 V) ; surtensions inductives des câbles de rubans | Destruction MOSFET | Faible | Arbitrage au livrable PCB (MOSFET 60 V) |
| R-11 | Trafic ESP-NOW hostile ou accidentel (même `net_id`) | Spectacle perturbé | Faible | `net_id` aléatoire recommandé, A4 pour les commandes |
| R-12 | Wi-Fi voisin intense sur le même canal (salle, festival) | Pertes, latence | Moyenne | Choix du canal (scan documenté), débit, CLI affichant les pertes |
| R-13 | Ondulation excessive dans C7 | Vieillissement de C7 | Moyenne | Condensateur faible ESR + déphasage PWM (§4.6) |
| R-14 | V-cut sur une carte de 50 mm de haut refusé ou non standard chez JLCPCB | Surcoût, découpe différente | Moyenne | [V-HW-12] ; repli : languettes à perforations |
| R-15 | Boîtier ignifugé difficile à imprimer (gauchissement) | Retard | Moyenne | Géométrie sans grands aplats, congés, bordure ; test d'impression tôt |

---

## 8. Critères d'acceptation par livrable

### 8.1 Protocole (ce document + PROTOCOL.md)
- Validation explicite par toi ; arbitrages A1 à A8 tranchés (fait le 2026-09-25, §9).

### 8.2 PCB
- ERC et DRC `kicad-cli` sans erreur ni avertissement non justifié (exceptions listées).
- Règles de classes de réseaux : MAINS ↔ LV ≥ 6 mm ; MAINS ↔ MAINS ≥ 3 mm ; pistes de
  puissance ≥ largeurs §4.8.3 ; aucun cuivre MAINS à < 4 mm de l'axe de découpe (vérifié
  par script).
- Fichiers JLCPCB : Gerber, perçage, V-cut, BOM (`bom_base` et `bom_led`, A7) et CPL au format JLCPCB, rendus PNG
  dessus/dessous ; génération reproductible par une commande (`make -C hardware`).
- `hardware/REVIEW.md` : liste de contrôle de relecture humaine complétée.
- Recommandation (hors CI) : test diélectrique secteur/TBT au premier prototype
  (3 kV AC ou 4,2 kV DC, 60 s, par une personne équipée) et essai de charge à 10 A pendant
  1 h avec relevé thermique.

### 8.3 Firmware nœud
- Compilation CI (pioarduino épinglé) sans avertissement bloquant.
- Tests natifs verts : CRC (vecteur `0x29B1`), codec en-tête et types, validation et
  rejets, réassemblage (ordre, pertes, doublons, fusion partielle), anti-rebond relais
  (différé, dernier état, priorités), gamma (bornes, monotonie, linéaire à 1,0), TLV,
  compteur de pertes (bouclage 16 bits), vecteurs communs.
- Recette sur banc : DMX mesuré à l'analyseur logique (timings, cadence), relais,
  PWM (fréquence, résolution, déphasage), maintenance et OTA, perte de flux.

### 8.4 Firmware dongle
- Compilation CI ; tests natifs (COBS, ordonnancement, répétition, `hold_timeout`, suivi
  des commandes et retransmissions) ; recette : latence mesurée ≤ budget §5.1.

### 8.5 Démon Pi
- `pytest` vert : parsing Art-Net (ArtDmx, ArtPoll/Reply), COBS, CRC, encodage des trames,
  vecteurs communs, gestion de reconnexion (dongle simulé par pseudo-terminal).
- `install.sh` testé sur Raspberry Pi OS Bookworm (ou conteneur Debian Bookworm en CI) ;
  service démarré, redémarrage automatique vérifié.
- CI : compilation des firmwares, tests natifs, tests Python, ERC/DRC, export boîtier.

### 8.6 Boîtier
- Export STL et STEP sans erreur pour les deux variantes ; solides valides (`isValid()`),
  fermés ; vérification scriptée des jeux (PCB + 0,5 mm), épaisseurs de paroi ≥ 2 mm, zone
  sans métal autour de l'antenne ; rendu PNG assemblé.

### 8.7 Documentation
- Documents listés au cahier des charges ; liste de contrôle sécurité avant mise sous
  tension ; relue par toi.

---

## 9. Arbitrages (tranchés le 2026-09-25)

| ID | Sujet | Décision | Alternative écartée |
|----|-------|----------|---------------------|
| A1 | Alimentation interne (décision 4) | **Mean Well IRM-05-5** (certifié 62368-1) ; HLK-PM05 en empreinte de repli | HLK-PM05 par défaut |
| A2 | Protection du chemin de charge | **Cuivre dimensionné 16 A**, charge nominale déclarée 10 A, pas de fusible de charge | Fusible 10 A sur carte |
| A3 | Longueur des trames DMX | **`dmx_out_slots` défaut 512**, réglage à la mise en service, avertissement CLI | Défaut court (64) |
| A4 | Authentification des commandes (PROTOCOL §7) | **Oui**, HMAC tronqué + compteur, clé facultative (enrôlement) | `net_id` seul |
| A5 | Balayage des canaux après 60 s sans réseau | **Oui** | Canal fixe strict |
| A6 | Maintenance sans ouvrir le boîtier | **Option configurable** `powercycle_maint` : 3 mises sous tension rapprochées (< 5 s), activée par défaut (révisé le 2026-09-25) | Toujours active ; BOOT seulement |
| A7 | LED d'état | **Option** : empreinte D4/R19 sur IO0 toujours présente, non montée par défaut, clé `status_led` (défaut 0), option boîtier `light_pipe` (révisé le 2026-09-25) | Pas de LED ; LED systématique |
| A8 | ESP-NOW v2 + pioarduino (ADR 0011) | **Oui**, repli v1 fragmenté implémenté | v1 fragmenté seul |

Question ouverte sans proposition : **J3-3V3** — programmer en injectant 3,3 V sur la
sortie de U3 alimente la sortie d'un régulateur non alimenté ; le comportement de
l'AP2112K en courant inverse est à vérifier [V-HW-05]. Si non garanti, je proposerai de
remplacer la pastille J3-3V3 par J3-5V (alimentation par l'entrée du régulateur).

---

## 10. À valider

| ID | Hypothèse | Source à consulter | Criticité |
|----|-----------|--------------------|-----------|
| V-HW-01 | HLK-PM05 (empreinte de repli uniquement) : brochage (AC ×2, +Vo, −Vo), dimensions ~34 × 20 × 15 mm, pas des broches, isolation 3000 V AC, 600 mA, fusible et varistance recommandés | Fiche Hi-Link HLK-PM05 (hlktech.net) | 🔴 critique |
| V-HW-02 | ESP32-C3-MINI-1 : brochage des pastilles, GPIO exposés (0-10, 18-21), strapping IO2/IO8/IO9, zone d'exclusion d'antenne, consommations RX/TX, découplage recommandé | *ESP32-C3-MINI-1 Datasheet* et *ESP32-C3 Hardware Design Guidelines* (espressif.com) | critique |
| V-HW-03 | G5RL-U1A-E DC5 : courant et résistance de bobine (~80 mA / ~62 Ω supposés), disposition et diamètres des broches, distances bobine-contacts (ligne de fuite 8 mm annoncée), courant d'appel admissible, classe TV, homologations | Omron, fiche *G5RL-U/-K* K265-E1 (non accessible depuis cet environnement : proxy) | 🔴 critique |
| V-HW-04 | WAGO 2604-1103 (entrée latérale) / 2604-3103 (entrée par le dessus) : 3 pôles, pas 5 mm, 4 mm², 32 A / 320 V IEC (selon distributeurs), **une seule âme par point de serrage** ; références 2 et 5 pôles (2604-1102, 2604-1105 supposées) ; diamètre de perçage | Fiches WAGO 2604 (wago.com, non accessible depuis cet environnement) | 🔴 critique |
| V-HW-05 | AP2112K-3.3 : brochage SOT-23-5 (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT), RθJA, comportement en courant inverse | Diodes Inc., fiche AP2112 | moyenne |
| V-HW-06 | SP3485 : brochage SOIC-8 (1 RO, 2 /RE, 3 DE, 4 DI, 5 GND, 6 A, 7 B, 8 VCC), courant de sortie ; SM712 brochage SOT-23 | MaxLinear SP3485 ; Semtech ou Bourns SM712 | moyenne |
| V-HW-07 | AOD4184A : RDS(on) à VGS 4,5 et 5 V, Qg, énergie d'avalanche ; AO3400 : VGS(th) | Alpha & Omega Semiconductor | moyenne |
| V-HW-08 | C7 470 µF 35 V : courant d'ondulation admissible, ESR, diamètre ; porte-fusible ATO pour PCB (référence type Keystone 3557-2, intensité admissible 20 A ?) | Fabricants, catalogue LCSC | moyenne |
| V-HW-09 | Mean Well IRM-05-5 : brochage, dimensions (~33,7 × 22,2 × 15 mm supposées), homologations, fusible et varistance recommandés en entrée | Fiche Mean Well IRM-05 | 🔴 critique |
| V-HW-10 | Faisabilité du placement dans 90 × 50 mm | Livrable PCB | moyenne |
| V-HW-11 | Valeurs normatives exactes (IEC 62368-1 tableaux de distances dans l'air et lignes de fuite pour isolation renforcée, 250 V, PD2, OVC II, groupe IIIb) | Norme IEC 62368-1:2018 (ou EN 62368-1:2020+A11) | 🔴 critique |
| V-HW-12 | Règles JLCPCB : V-cut sur carte unique (dimensions minimales), distance cuivre/V-cut, fentes ≥ 1 mm, cuivre 2 oz en 2 couches | jlcpcb.com, capacités de fabrication | moyenne |
| V-HW-13 | Disponibilité JLCPCB/LCSC des références et coût de l'assemblage traversant | LCSC | faible |
| V-FW-01 | pioarduino : version exacte à épingler (Arduino ≥ 3.2 / IDF ≥ 5.4.2), support ESP32-C3 et XIAO ESP32-C3 | github.com/pioarduino/platform-espressif32 (releases) | critique |
| V-FW-02 | `esp_now_set_peer_rate_config()` utilisable pour le pair broadcast depuis Arduino 3.x | ESP-IDF API ESP-NOW (v5.5) | moyenne |
| V-FW-03 | `esp_dmx` compatible Arduino 3.x / IDF 5.5 sur ESP32-C3 ; `dmx_send_num()` | github.com/someweisguy/esp_dmx | moyenne (repli prévu) |
| V-FW-04 | Débit et latence réels de l'USB Serial/JTAG de l'ESP32-C3 côté Linux | Mesure sur banc | moyenne |
| V-FW-05 | Réception ESP-NOW maintenue en mode AP+STA | Mesure ; ESP-IDF doc ESP-NOW (coexistence) | faible |
| V-FW-06 | Retour arrière OTA disponible avec le chargeur d'amorçage précompilé d'Arduino 3.x | Documentation Arduino-ESP32 | faible |
| V-FW-07 | Format exact de la trame ESP-NOW v2 (surcoût en octets) | ESP-IDF doc ESP-NOW, *Frame Format* | faible (affecte le calcul d'occupation de ±10 %) |
| V-FW-08 | QLC+ : sortie Art-Net vers 127.0.0.1 possible, cadence (50 Hz), mode d'émission « complet / partiel », réception des ArtPollReply sur loopback | Documentation QLC+ (plugin Art-Net) ; essai | moyenne |
| V-ENC-01 | Diamètres des cordons secteur et DMX retenus ; plages de serrage des presse-étoupes | Fiches câbles et presse-étoupes | moyenne |
| V-ENC-02 | Filament ignifugé retenu : classement UL94 et épaisseur associée, conditions d'impression | Fiche technique du filament | 🔴 critique |
| V-SYS-01 | Puissance maximale des projecteurs visés et courant d'appel mesuré | Toi (inventaire du parc) | moyenne |
| V-SYS-02 | XLR 3 ou 5 broches sur le parc | Toi | faible |

---

## 11. Réponses aux points ouverts du cahier des charges

1. **WAGO 2604 et double sortie J4** : références supposées 2604-1103 / 2604-3103
   (3 pôles), 2604-1102 (2 pôles), 2604-1105 (5 pôles), pas 5 mm [V-HW-04]. Une borne
   2604 n'accepte qu'un conducteur par point : **seconde borne J4b** 3 pôles en parallèle
   de J4 (L_SW, N, PE), pistes dimensionnées pour le courant total. Entrée par le dessus
   (-3103) ou latérale (-1103) à choisir au placement selon l'orientation des
   presse-étoupes.
2. **Brochages PS1, U1, K1** : non vérifiables depuis cet environnement (sites fabricants
   bloqués) ; hypothèses en V-HW-01 à 03, vérification obligatoire au livrable PCB, avec
   empreintes construites **depuis la fiche** et cotes citées dans `hardware/REVIEW.md`.
3. **ESP-NOW v2** : disponible depuis ESP-IDF 5.4 (1470 octets à partir de 5.4.2),
   accessible en Arduino 3.2+ via pioarduino. Retenu, repli v1 fragmenté (ADR 0011).
4. **Puissance des projecteurs et XLR** : G5RL dimensionné pour ~500 W de LED
   (appels de courant) ; à confirmer par ton inventaire [V-SYS-01/02]. Boîtier et queue
   prévus en NC3FXX par défaut, NC5FXX en option (broches 4 et 5 non connectées).
5. **Matériau** : ABS-FR V-0 recommandé (§4.12).

---

## 12. Outillage (état de l'environnement de développement au 2026-09-25)

| Outil | État | Action proposée |
|-------|------|-----------------|
| Git 2.43 | présent | — |
| Python 3.11 | présent | — |
| Java (OpenJDK 21) | présent | nécessaire à Freerouting |
| KiCad 8+ / `kicad-cli` | **absent** (dépôt Ubuntu : KiCad 7.0 seulement) | PPA KiCad 8/9 ou image Docker `kicad/kicad` en CI |
| SKiDL | **absent**, disponible sur PyPI (2.3.0) | `pip install skidl` |
| CadQuery | **absent**, disponible sur PyPI (2.8.0) | `pip install cadquery` |
| Freerouting | **absent** | JAR depuis les releases GitHub |
| PlatformIO | **absent**, disponible sur PyPI | `pip install platformio` + plateforme pioarduino |
