# Relecture humaine du PCB dmxnow

> 🔴 **RELECTURE HUMAINE OBLIGATOIRE avant toute commande et toute mise sous tension.**
> Ce PCB a été conçu et routé par script. Les contrôles automatiques (ERC, DRC avec
> règles 230 V personnalisées, cohérence netlist) ne remplacent pas la relecture d'une
> personne qualifiée en électronique de puissance et en sécurité électrique.

Cocher chaque ligne, noter le nom du relecteur et la date. Tout point non conforme
bloque la commande.

Relecteur : ____________________  Date : ____________  Révision PCB : 0.3

## 1. Empreintes (bloquant)

Les cotes de K1, des WAGO 2604 et de PS1 ont été relevées sur les fiches constructeur
(liste et liens : `datasheets/README.md`) et sont centralisées dans `gen/footprints.py`
(dictionnaire `DIMS`, avec la page source). Les confronter aux fiches et, idéalement, à
une pièce réelle posée sur une impression 1:1 du PCB.

| Réf. | Composant | Cotes relevées | Source | OK |
|------|-----------|----------------|--------|----|
| K1 | Omron G5RL-1A-E-HR DC5 (LCSC C113250) | Bobine 1/8 → A1 (0 ; 0) et A2 (7,5 ; 0), COM 3/6 → 13 en (0 ; 20) et (7,5 ; 20), NO 4/5 → 14 en (0 ; 25) et (7,5 ; 25), perçage 1,3 mm, corps 29,0 × 12,7 × 15,7 mm max. Bobine 80 mA / 62,5 Ω, isolation renforcée 8 mm / 10 kV. **Ne pas accepter de G5RL-U1A-E (bistable).** | Catalogue Omron G5RL p. 5 | ☐ |
| J1, J4, J7, J5 | WAGO 2604-1102 (LCSC C3309286) | Pas 5,0 mm, 2 broches par pôle à 8,2 mm, perçage 1,4 mm (fiche : 1,3 +0,1 ; tolérance JLCPCB −0,08), broche 0,8 × 1 mm, pastilles 2,0 × 2,8 mm, corps 16,3 mm (broche avant à 5,2 mm de la face d'entrée, arrière à 2,9 mm du dos), levier 2,9 mm en saillie, largeur 12,4 mm. Le corps dépasse le bord du PCB de 1,4 mm (J1, J4, J7) et 0,7 mm (J5, J6). | Fiche WAGO 2604-1102 p. 2 | ☐ |
| J6 | WAGO 2604-1105 | Même série, 5 pôles, largeur 27,4 mm (formule de la fiche 2604-1102) ; fiche 5 pôles non consultée. | Fiche WAGO 2604-1105 | ☐ |
| PS1 | Mean Well IRM-03-5 (LCSC C6969425) | Empreinte KiCad `Converter_ACDC_MeanWell_IRM-03-xx_THT` conforme : AC/L (1), AC/N (3) à 5,08 mm, NC (5) à 30,48 mm, −Vo (14) et +Vo (16) à 17,78 mm, broches Ø 0,6 mm, corps 37 × 24 × 15 mm. | Fiche IRM-03 (2025-08-08) p. 4 | ☐ |
| F1 | Support Schurter 0031.8201 (LCSC C3204125) + cartouche Littelfuse 0215.500MXP (T500 mA H, céramique, 1500 A sous 250 V AC, LCSC C142839, à insérer à la main) | Empreinte KiCad `Fuseholder_Cylinder-5x20mm_Schurter_0031_8201_Horizontal_Open` : broches à 22,5 mm, ergot NPTH de 2,7 mm. Vérifier sur la fiche Schurter. Support ouvert : pièces nues sous 230 V dans le compartiment secteur. | Schurter | ☐ |
| U1 | ESP32-C3-MINI-1 | Empreinte officielle Espressif (kicad-libraries), zone d'exclusion d'antenne incluse. Vérifier la version de l'empreinte. | Espressif | ☐ |
| F2 | Porte-fusible ATO | Empreinte KiCad Littelfuse FLR 178.6165 ; vérifier l'intensité admissible (≥ 20 A) et la disponibilité. | Littelfuse | ☐ |

Si une cote diffère : corriger `DIMS`, relancer `make lib pcb route check fab`.

## 2. Isolement 230 V / basse tension 🔴

| # | Point | Référence | OK |
|---|-------|-----------|----|
| 2.1 | Toute pièce de cuivre 230 V (nets L_IN, L_SW, N, L_PSU) est à X ≤ 46 mm ; tout cuivre basse tension à X ≥ 52 mm (6 mm). Vérifié par la règle DRC `mains_to_low_voltage` et par `check.py pcb` ; contrôler visuellement sur les Gerbers. | SPEC 4.8.2 | ☐ |
| 2.2 | Fentes de 1 mm à X = 49 mm sous K1 (Y 12-26) et sous PS1 (Y 27,5-52), entre broches AC et DC de PS1 et entre contacts et bobine de K1. | SPEC 4.8.2 | ☐ |
| 2.3 | Distance bobine-contacts de K1 (interne au relais) ≥ distance requise pour l'isolation renforcée : la fiche Omron annonce une isolation renforcée, 8 mm dans l'air et en ligne de fuite, 6000 V AC, choc 10 kV (à confronter à IEC 62368-1, V-HW-11). | V-HW-03 | ☐ |
| 2.4 | Isolation entrée-sortie de PS1 certifiée (IEC/UL 62368-1) : marquage d'homologation présent sur la pièce achetée. | V-HW-09 | ☐ |
| 2.5 | Aucun plan de masse, via, piste ou trou métallisé basse tension dans la zone 230 V, sur les deux faces. | SPEC 4.8.2 | ☐ |
| 2.6 | Aucun trou de fixation dans la zone 230 V (une vis métallique annulerait l'isolement). | design.py | ☐ |
| 2.7 | Ligne de découpe (X = 100 mm, fente + 3 languettes perforées) : aucun cuivre 230 V à moins de 4 mm, aucun composant à moins de 4 mm ; seuls PWM1-4, BOARD_SENSE, +5V et GND la traversent, sur les languettes. | SPEC 4.8.4, `check.py pcb` | ☐ |
| 2.8 | Distances entre nets 230 V ≥ 3 mm, sauf exceptions acceptées : pastilles COM/NO de K1 (2,4 mm, fixées par le relais) et broches AC de PS1 (2,93 mm, fixées par le module). Règle `mains_pad_to_pad_inside_components`, limitée aux pastilles de K1 et de PS1. | SPEC 4.8.2 | ☐ |
| 2.10 | Broche 5 (NC) de PS1 : elle est sur la rangée AC du module ; traitée comme primaire : aucun cuivre à moins de 6 mm du bord de la pastille (règle DRC `ps1_nc_pin`, zone interdite `ps1_nc_keepout`). Confirmer auprès de Mean Well qu'elle n'est reliée à rien (ou mesurer : continuité et essai diélectrique). | SPEC 4.3 | ☐ |
| 2.11 | F1 : fusible céramique à haut pouvoir de coupure (1500 A) ; ne jamais le remplacer par un fusible en verre (35 A). | SPEC 4.3 | ☐ |
| 2.9 | Le PE ne passe pas par le PCB : les trois conducteurs PE sont réunis par un WAGO 221-413 dans le compartiment 230 V du boîtier (arbitrage A9). | SPEC 4.12 | ☐ |

## 3. Chemins de puissance

| # | Point | Référence | OK |
|---|-------|-----------|----|
| 3.1 | Chemin de charge L_IN → K1 → L_SW : L_IN 4 à 4,3 mm sur les deux faces ; L_SW en doigts de 7,4 mm et bus de 7 mm sur la face avant. Col de 1,9 mm sur ≤ 8 mm aux broches des borniers (imposé par le pas de 5 mm). Juger l'échauffement à 16 A. | SPEC 4.8.3, A2 | ☐ |
| 3.2 | N : bus de 7,1 mm et doigts de 3,4 à 4 mm en face arrière ; col de 3,4 mm sur ~8 mm entre J1 et le bus (~30 °C à 16 A selon IPC-2221, à mesurer au thermocouple). Juger l'échauffement à 16 A (estimation IPC-2221 : ≤ 10 °C sur le bus, ~25 °C sur les cols). | SPEC 4.8.3 | ☐ |
| 3.3 | Branche L_PSU / N vers PS1 et RV1 : 1 mm (courant < 50 mA, protégée par F1). | — | ☐ |
| 3.4 | Partie rubans : VLED en plan (face avant), GND_LED en plan (face arrière), VLED_IN 4,5 mm, canaux 2,5 mm (6 A). | SPEC 4.6 | ☐ |
| 3.5 | Sources des MOSFET (AOD2610E, 60 V) reliées au plan GND_LED par 3 vias de 0,6 mm chacune ; vérifier la capacité (≈ 4 à 6 A par MOSFET). | — | ☐ |
| 3.7 | F2 : fusible ATO chargé à ≤ 80 % de son calibre en continu (20 A pour ≤ 16 A, sinon 25 A ; support 30 A). Polarité de J5 marquée « + / − » : une inversion met D3 en court-circuit. VLED ≤ 28 V. | SPEC 4.6, V-HW-08 | ☐ |
| 3.8 | Courant d'appel des charges sur J4/J4b ≤ ~80 A crête (G5RL-1A-E-HR : 100 A) : mesuré sur les charges réelles. | V-SYS-01 | ☐ |
| 3.6 | GND logique et GND_LED reliées en un seul point : R20 (0 Ω 0805) près de U4. BOARD_SENSE relié à GND par R21 (0 Ω) sur la partie sécable. Plans : GND logique (deux faces, X 100-113) et GND_LED (face arrière, X ≥ 113) séparés. | SPEC 4.8.4 | ☐ |

## 4. Basse tension

| # | Point | OK |
|---|-------|----|
| 4.1 | Antenne de U1 en bord de carte, aucune piste, via ni plan dans la zone d'exclusion (règle `antenna_keepout`), rien de métallique au-dessus dans le boîtier. | ☐ |
| 4.2 | Découplage : C1 (47 µF) et C2 (100 nF) au plus près de la broche 3V3 de U1 ; C3 contre U2 ; C9 contre U4. | ☐ |
| 4.3 | Pull-ups de démarrage R2 (IO9), R3 (IO8), R4 (IO2), RC d'EN (R1, C4). R15-R18 4,7 kΩ (GPIO6 a une résistance de tirage interne au reset), R22 10 kΩ sur DMX_TX, R23 100 kΩ sur BOARD_SENSE. | ☐ |
| 4.4 | SW1 accessible par le poussoir du couvercle ; J3 accessible couvercle basse tension ouvert. | ☐ |
| 4.5 | Échauffement de U3 (AP2112K) : cuivre suffisant autour de la broche GND (plan). | ☐ |
| 4.6 | Routage automatique (Freerouting) : longueur et aspect des pistes USB (D-/D+) acceptables pour la programmation. | ☐ |

## 5. Fabrication

| # | Point | OK |
|---|-------|----|
| 5.1 | JLCPCB : 2 couches, 1,6 mm, **cuivre 2 oz**, FR-4 TG ≥ 150, finition HASL sans plomb ou ENIG. | ☐ |
| 5.2 | Séparation : fente fraisée et trous de perforation inclus dans les Gerbers (Edge.Cuts, NPTH). Préciser en remarque de commande : « single design, internal routed slot with breakaway tabs, do not separate ». JLCPCB peut la compter comme panneau de 2 designs : accepter ou discuter. | ☐ |
| 5.3 | Fentes internes de 1 mm présentes sur le calque Edge.Cuts. | ☐ |
| 5.4 | BOM et CPL (`fab/*_full.csv` pour CMS + traversants, `*_smt.csv` pour CMS seuls) : références LCSC vérifiées le 2026-09-26 (revérifier le stock ; WAGO 2604-1105 (J6) en rupture chez LCSC : consigner ou souder à la main). Rotations et centres convertis aux conventions JLCPCB (`fab.py`, `JLC_FIX`) ; F1 (support Schurter) sans correction connue ; rotations des composants à contrôler dans l'aperçu JLCPCB. | ☐ |
| 5.5 | Composants traversants (WAGO, K1, PS1, F1, RV1, F2, C7) soudés à la main ou en assemblage traversant. | ☐ |

## 6. Essais du premier prototype (personne équipée et qualifiée)

1. Inspection visuelle, continuité, absence de court-circuit L/N, L/basse tension, N/basse tension.
2. Essai diélectrique secteur ↔ basse tension (toutes broches TBT reliées) : 3 kV AC ou
   4,2 kV DC pendant 60 s, sans claquage.
3. Première mise sous tension derrière un transformateur d'isolement et un disjoncteur
   différentiel 30 mA, charge résistive.
4. Essai de charge : 10 A pendant 1 h, relevé thermique (pistes, relais, borniers) ;
   essai de courte durée à 16 A.
5. Commutation d'une alimentation LED réelle (courant d'appel), 1000 cycles.
