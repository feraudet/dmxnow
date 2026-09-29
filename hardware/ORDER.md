# Commande JLCPCB : première série (5 nœuds montés)

🔴 **Avant de payer** : relecture humaine de [`REVIEW.md`](REVIEW.md) (sections 1 et 2
en priorité) faite et signée, CI `hardware` verte sur le commit commandé.

Estimation : **~335 à 400 € TTC** pour les 5 cartes montées livrées, **~125 à 150 €**
d'achats hors JLCPCB, soit **~500 € TTC** pour 5 nœuds (prix JLCPCB du 2026-09-27 ;
le devis en ligne fait foi).

## 1. Fichiers à déposer

| Étape du site | Fichier |
|---------------|---------|
| Gerber | `fab/dmxnow-gerbers.zip` |
| BOM | `fab/bom_jlcpcb_full.csv` |
| CPL (placement) | `fab/cpl_jlcpcb_full.csv` |

Variante avec la LED d'état (option A7) : `bom_jlcpcb_full_led.csv` +
`cpl_jlcpcb_full_led.csv`. Par défaut, **sans LED**.

## 2. Réglages PCB

| Paramètre | Valeur |
|-----------|--------|
| Base material | FR-4, TG ≥ 150 si proposé |
| Layers | 2 |
| Dimensions | reprises des Gerbers : 146 × 65,5 mm |
| PCB Qty | 5 |
| Delivery format / Panel | **Panel by Customer**, 1 × 1 |
| Different Design | **2** (JLCPCB compte la fente fraisée et les languettes comme 2 circuits) |
| PCB Thickness | 1,6 mm |
| PCB Color / Silkscreen | vert / blanc (le moins cher, délai standard) |
| Surface Finish | HASL sans plomb (ou ENIG) |
| **Outer Copper Weight** | **2 oz** (indispensable : chemins 16 A et 17 A) |
| Via Covering | Tented |
| Remove Order Number | Yes |
| Castellated holes, edge plating | No |

**Remarque de commande (PCB et PCBA)**, à copier telle quelle :

> One circuit with an internal routed slot and 3 breakaway tabs carrying traces; deliver
> and assemble as one piece, do NOT separate. SMT: convey on the straight short edges X=0
> and X=146; U1/Q5/R10 are close to the Y=54 edge by design. J3, J2 not populated: keep
> holes open (no solder fill). J1, J4, J7, J5, J6, J8: wire entry toward board edge; J6
> and J8 side by side. RV1: form leads to the PCB holes. F2: press flat before soldering.
> F1/F2 fuses are not fitted.

## 3. Réglages PCBA

| Paramètre | Valeur |
|-----------|--------|
| PCBA Type | **Standard** (module ESP32 et composants traversants) |
| Assembly Side | Top Side |
| PCBA Qty | **5** |
| Tooling holes / edge rails | selon la proposition de JLCPCB (voir la remarque : convoyage par les petits côtés) |
| Confirm Parts Placement | **Yes** (JLCPCB envoie l'aperçu à valider) |

Après dépôt de la BOM : **32 lignes, 56 composants placés**, toutes « in stock » (le
WAGO 2604-1102 C3309286 apparaît sur 5 lignes, une par bornier : normal). J2 (queue DMX),
J3 (pastilles de programmation), R19 et D4 (option LED) ne sont pas dans la BOM : normal.
Revérifier le stock des références à faible stock :

| Réf. | LCSC | Stock au 2026-09-27 | Besoin |
|------|------|---------------------|--------|
| K1 G5RL-1A-E-HR | C113250 | 232 | 5 |
| J8 WAGO 2604-1103 | C3309758 | 356 | 5 |
| J1/J4/J5/J6/J7 WAGO 2604-1102 | C3309286 | 594 | 25 |
| F2 porte-fusible ATO | C207061 | 617 | 5 |
| PS1 IRM-03-5 | C6969425 | 992 | 5 |

## 4. Aperçu de placement : points à contrôler

JLCPCB montre chaque composant sur la carte ; comparer à la sérigraphie :

- **Q2 à Q5** (DPAK) : languette (grande pastille) vers les borniers J6/J8 (vers la droite).
- **U1** (ESP32-C3) : zone d'antenne vers le bord supérieur, sur la mention « Antenna Area ».
- **C7** (électrolytique) : « + » sur la pastille carrée, à gauche.
- **D3** (SMBJ28A) : cathode (bande) vers le haut, côté C7 / VLED.
- **U2, U3, U4, D1, Q1** : point de la broche 1 sur le repère de la sérigraphie.
- **PS1** : broche 1 (carrée) en bas à gauche, côté RV1 ; **K1** : bobine côté droit (x ≈ 53).
- **WAGO J1, J4, J7** : entrée des fils vers le bord gauche ; **J5, J6, J8** : vers le bord droit.
- **F1, F2** : supports seulement (fusibles non fournis).

## 5. Achats hors JLCPCB (5 nœuds + rechanges)

| Article | Qté | Note |
|---------|-----|------|
| Fusible 5×20 mm **T500 mA H 250 V** (Littelfuse 0215.500MXP ou équivalent céramique) | 10 | F1, dont 5 de rechange |
| Fusible ATO **20 A** | 10 | F2, dont 5 de rechange |
| WAGO 221-413 | 5 | Jonction des PE (A9) |
| Presse-étoupe plastique M16 × 1,5 (serrage 4,5-10 mm) + contre-écrou | 25 | Carte entière : 5 par boîtier |
| Presse-étoupe plastique M12 × 1,5 (serrage jusqu'à 7 mm) + contre-écrou | 5 | Queue DMX |
| Inserts M3 à chaud Ø 4,0 × 5,7 | 80 | 16 par boîtier |
| Vis M3 × 6 / M3 × 16 | 50 / 30 | Couvercles + PCB / étriers |
| Filament **ABS-FR ou PC-ABS-FR UL94 V-0** | 1 kg | ~750 g utiles ; garder la fiche technique [V-ENC-02] 🔴 |
| Câble DMX 120 Ω + Neutrik NC3FXX | 5 m + 5 | Queues de 1 m |
| Câble secteur H05VV-F 3G1,5 + fiches | selon installation | Hors estimation |

Pour la programmation : une rallonge ou un adaptateur USB (5 V, GND, D−, D+) à relier
aux pastilles J3 ; alimenter par **J3-5V**, jamais par J3-3V3 (REVIEW 7.6).

## 6. À réception

Suivre [`REVIEW.md`](REVIEW.md) §6 : inspection, continuité, **essai diélectrique
secteur ↔ basse tension**, première mise sous tension derrière transformateur d'isolement
et différentiel 30 mA.
