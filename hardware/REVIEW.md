# Relecture humaine du PCB dmxnow

> 🔴 **RELECTURE HUMAINE OBLIGATOIRE avant toute commande et toute mise sous tension.**
> Ce PCB a été conçu et routé par script. Les contrôles automatiques (ERC, DRC avec
> règles 230 V personnalisées, cohérence netlist) ne remplacent pas la relecture d'une
> personne qualifiée en électronique de puissance et en sécurité électrique.

Cocher chaque ligne, noter le nom du relecteur et la date. Tout point non conforme
bloque la commande.

Relecteur : ____________________  Date : ____________  Révision PCB : 0.1

## 1. Empreintes provisoires (bloquant)

Les fiches constructeur n'étaient pas accessibles depuis l'environnement de conception.
Les cotes ci-dessous sont **supposées** ; elles sont centralisées dans
`gen/footprints.py` (dictionnaire `DIMS`) et marquées « PROVISOIRE » sur le calque
User.Comments de chaque empreinte.

| Réf. | Composant | Cotes à vérifier sur la fiche | Source | OK |
|------|-----------|-------------------------------|--------|----|
| K1 | Omron G5RL-U1A-E DC5 | Implantation reprise de l'Omron G2RL-1A-E : bobine A1 (0 ; 0) et A2 (7,5 ; 0), COM (13) en (0 ; 20) et (7,5 ; 20), NO (14) en (0 ; 25) et (7,5 ; 25), perçage 1,3 mm, corps 12,5 × 28,8 mm. Vérifier aussi le nombre de broches par contact, la ligne de fuite bobine-contacts (8 mm annoncés) et le courant de bobine (~80 mA supposés). | Omron K265-E1 (G5RL-U/-K) | ☐ |
| J1, J4, J7 | WAGO 2604-1102 | Pas 5,0 mm, **2 broches par pôle écartées de 6,0 mm**, perçage 1,3 mm, corps 10 × 18 mm, entrée de fil latérale. | Fiche WAGO 2604-1102 | ☐ |
| J5 | WAGO 2604-1102 | idem | idem | ☐ |
| J6 | WAGO 2604-1105 | idem, 5 pôles | Fiche WAGO 2604-1105 | ☐ |
| PS1 | Mean Well IRM-03-5 | Empreinte KiCad `Converter_ACDC_MeanWell_IRM-03-xx_THT` : broches AC/L (1), AC/N (3), NC (5), −Vo (14), +Vo (16). Vérifier hauteur (~15 mm) et fusible/varistance recommandés en entrée. | Fiche Mean Well IRM-03 | ☐ |
| U1 | ESP32-C3-MINI-1 | Empreinte officielle Espressif (kicad-libraries), zone d'exclusion d'antenne incluse. Vérifier la version de l'empreinte. | Espressif | ☐ |
| F2 | Porte-fusible ATO | Empreinte KiCad Littelfuse FLR 178.6165 ; vérifier l'intensité admissible (≥ 20 A) et la disponibilité. | Littelfuse | ☐ |

Si une cote diffère : corriger `DIMS`, relancer `make lib pcb route check fab`.

## 2. Isolement 230 V / basse tension 🔴

| # | Point | Référence | OK |
|---|-------|-----------|----|
| 2.1 | Toute pièce de cuivre 230 V (nets L_IN, L_SW, N, L_PSU) est à X ≤ 46 mm ; tout cuivre basse tension à X ≥ 52 mm (6 mm). Vérifié par la règle DRC `mains_to_low_voltage` et par `check.py pcb` ; contrôler visuellement sur les Gerbers. | SPEC 4.8.2 | ☐ |
| 2.2 | Fentes de 1 mm à X = 49 mm sous K1 (Y 12-26) et sous PS1 (Y 27,5-52), entre broches AC et DC de PS1 et entre contacts et bobine de K1. | SPEC 4.8.2 | ☐ |
| 2.3 | Distance bobine-contacts de K1 (interne au relais) ≥ distance requise pour l'isolation renforcée : vérifier sur la fiche Omron (ligne de fuite 8 mm, 10 kV annoncés). | V-HW-03 | ☐ |
| 2.4 | Isolation entrée-sortie de PS1 certifiée (IEC/UL 62368-1) : marquage d'homologation présent sur la pièce achetée. | V-HW-09 | ☐ |
| 2.5 | Aucun plan de masse, via, piste ou trou métallisé basse tension dans la zone 230 V, sur les deux faces. | SPEC 4.8.2 | ☐ |
| 2.6 | Aucun trou de fixation dans la zone 230 V (une vis métallique annulerait l'isolement). | design.py | ☐ |
| 2.7 | Ligne de découpe (X = 100 mm) : aucun cuivre 230 V à moins de 4 mm, aucun composant à moins de 4 mm ; seuls PWM1-4, BOARD_SENSE, +5V et GND la traversent. | SPEC 4.8.4, `check.py pcb` | ☐ |
| 2.8 | Distances entre nets 230 V ≥ 3 mm, sauf exceptions acceptées : pastilles COM/NO de K1 (2,4 mm, fixées par le relais) et broches AC de PS1 (2,93 mm, fixées par le module). Règle `mains_pad_to_pad_inside_components`. | SPEC 4.8.2 | ☐ |
| 2.9 | Le PE ne passe pas par le PCB : les trois conducteurs PE sont réunis par un WAGO 221-413 dans le compartiment 230 V du boîtier (arbitrage A9). | SPEC 4.12 | ☐ |

## 3. Chemins de puissance

| # | Point | Référence | OK |
|---|-------|-----------|----|
| 3.1 | Chemin de charge L_IN → K1 → L_SW : bandes ≥ 4 mm doublées sur les deux faces (≥ 8 mm équivalents), bus L_SW 5 mm sur les deux faces entre les broches NO. Col de 1,9 à 3,5 mm sur ≤ 8 mm aux broches des borniers (imposé par le pas de 5 mm). Juger l'échauffement à 16 A. | SPEC 4.8.3, A2 | ☐ |
| 3.2 | N : doigts 3,6 à 4 mm et bus 3,8 mm en face arrière seule. **Point d'attention** : section plus faible que L ; à 16 A, estimation IPC-2221 ΔT ≈ 25 °C. Proposer une couche d'étain (ouverture de vernis) si nécessaire. | SPEC 4.8.3 | ☐ |
| 3.3 | Branche L_PSU / N vers PS1 et RV1 : 1 mm (courant < 50 mA, protégée par F1). | — | ☐ |
| 3.4 | Partie rubans : VLED en plan (face avant), GND_LED en plan (face arrière), VLED_IN 4,5 mm, canaux 2,5 mm (6 A). | SPEC 4.6 | ☐ |
| 3.5 | Sources des MOSFET reliées au plan GND_LED par 2 vias chacune ; vérifier la capacité (≈ 4 A par MOSFET). | — | ☐ |
| 3.6 | GND logique et GND_LED reliées en un seul point (NT1, près de U4). | SPEC 4.8.4 | ☐ |

## 4. Basse tension

| # | Point | OK |
|---|-------|----|
| 4.1 | Antenne de U1 en bord de carte, aucune piste, via ni plan dans la zone d'exclusion (règle `antenna_keepout`), rien de métallique au-dessus dans le boîtier. | ☐ |
| 4.2 | Découplage : C1 (47 µF) et C2 (100 nF) au plus près de la broche 3V3 de U1 ; C3 contre U2 ; C9 contre U4. | ☐ |
| 4.3 | Pull-ups de démarrage R2 (IO9), R3 (IO8), R4 (IO2), RC d'EN (R1, C4). | ☐ |
| 4.4 | SW1 accessible par le poussoir du couvercle ; J3 accessible couvercle basse tension ouvert. | ☐ |
| 4.5 | Échauffement de U3 (AP2112K) : cuivre suffisant autour de la broche GND (plan). | ☐ |
| 4.6 | Routage automatique (Freerouting) : longueur et aspect des pistes USB (D-/D+) acceptables pour la programmation. | ☐ |

## 5. Fabrication

| # | Point | OK |
|---|-------|----|
| 5.1 | JLCPCB : 2 couches, 1,6 mm, **cuivre 2 oz**, FR-4 TG ≥ 150, finition HASL sans plomb ou ENIG. | ☐ |
| 5.2 | V-cut : fournir `fab/dmxnow-vcut.gbr` et le préciser dans la commande ; vérifier que JLCPCB accepte le V-cut sur une carte unique de 146 × 54 mm (sinon : languettes perforées). | ☐ |
| 5.3 | Fentes internes de 1 mm présentes sur le calque Edge.Cuts. | ☐ |
| 5.4 | BOM et CPL : références LCSC indicatives, à revalider ; rotations des composants à contrôler dans l'aperçu JLCPCB. | ☐ |
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
