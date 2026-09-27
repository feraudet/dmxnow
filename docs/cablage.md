# Câblage

🔴 **RELECTURE HUMAINE OBLIGATOIRE** pour les §1 et §2 (secteur). Tout le câblage se
fait **fiche secteur débranchée**. À la fin, dérouler la liste de contrôle de
[securite.md §4](securite.md) avant de brancher.

## Vue d'ensemble

```
            ┌──────────── boîtier du nœud (vue de dessus) ────────────────────────────┐
 secteur ──▶│ PE ─▶ WAGO 221-413 ◀─ PE ─┐                                              │
 (entrée)   │ L,N ─▶ J1 IN              │   ║cloison║                                 │
 projecteur◀│ L,N ◀─ J4 OUT 1  ◀── PE ──┤   ║       ║  ESP32 · DMX ─▶ J2 ─▶ XLR-3 ─────┼─▶ projecteur (DMX IN)
 alim. LED ◀│ L,N ◀─ J7 OUT 2  ◀── PE ──┘   ║       ║                                  │
            │  230 V (couvercle orange)      ║       ║  basse tension │ rubans  J5 ◀───┼── alim. LED 12/24 V
            │                                                         │ J6,J8 ─────────┼─▶ rubans
            └─────────────────────────────────────────────────────────────────────────┘
```

![Emplacement des borniers](figures/carte.svg)

Borniers : **WAGO 2604** à levier, conducteurs jusqu'à **4 mm²** (souple ou rigide),
dénudés sur **11 à 13 mm** [À valider : plage de section et longueur de dénudage à
relire sur la fiche WAGO 2604 de la pièce reçue]. Lever le levier, insérer à fond, rabattre. Sur fil souple, un embout
n'est pas nécessaire ; s'il est utilisé, sa longueur doit correspondre au dénudage.

## 1. Secteur 🔴

| Bornier | Sérigraphie | Raccorder |
|---------|-------------|-----------|
| **J1** | `IN L/N` | Câble d'entrée (vers la fiche secteur) : **L** (marron) et **N** (bleu) |
| **J4** | `OUT L/N` | Sortie 1, commutée par le relais : projecteur |
| **J7** | `OUT L/N` | Sortie 2, commutée par le relais : alimentation des rubans (ou second appareil) |
| **WAGO 221-413** | — | Les trois **PE** (vert-jaune) : entrée, sortie 1, sortie 2 |

- Câble recommandé : **H05VV-F 3G1,5** (Ø 8 à 9 mm, dans la plage du presse-étoupe M16).
- Le relais coupe la **phase** (L) des deux sorties ; le **neutre n'est pas coupé**.
  Respecter L et N, en particulier sur J1.
- Ordre de câblage : dénuder la gaine juste assez pour que les conducteurs arrivent aux
  borniers sans tension ; **PE d'abord** au 221-413, puis L et N. Le PE doit être le plus
  long : si le câble est arraché, il se débranche en dernier.
- Chaque câble : presse-étoupe serré **et** barre d'étrier (2 vis M3 × 16) serrée sur la
  gaine. Essai de traction à la main : les conducteurs ne bougent pas.
- Charges : **16 A au total** (J4 + J7) ; en pratique **un projecteur par nœud**
  (courant d'appel des alimentations à découpage, V-SYS-01). Si J7 n'est pas utilisé, le
  laisser vide, levier fermé, et fermer son presse-étoupe par un bouchon.

## 2. Mesures après câblage secteur 🔴

Fiche débranchée, à l'ohmmètre :
- continuité **PE** : broche de terre de la fiche d'entrée ↔ terre de chaque prise ou
  appareil de sortie (quelques centaines de mΩ au plus) ;
- pas de court-circuit L ↔ N, L ↔ PE, N ↔ PE à la fiche d'entrée (projecteur débranché) ;
- aucune continuité entre la fiche d'entrée et la queue DMX (broche 1) ni la borne « − »
  de J5.

## 3. DMX (queue J2 → XLR-3)

La sortie DMX est une **queue de câble** soudée sur les pastilles J2, sortie par le
presse-étoupe M12 et terminée par une **fiche XLR-3 femelle** (Neutrik NC3FXX), qui se
branche directement sur l'entrée DMX du projecteur.

| Pastille J2 | Signal | XLR-3 |
|-------------|--------|-------|
| 1 `GND` | Masse / blindage | **1** |
| 2 `B−` | Data − | **2** |
| 3 `A+` | Data + | **3** |

- Câble DMX 110 Ω (paire torsadée blindée), Ø 6 à 7 mm pour le presse-étoupe M12.
- Longueur de la queue : le nécessaire pour atteindre le projecteur ; au-delà, une
  rallonge DMX.
- La ligne se termine par **120 Ω** au dernier appareil : bouchon DMX sur la sortie DMX du
  projecteur s'il n'a pas de terminaison interne.
- Souder hors boîtier, gaine thermorétractable sur chaque soudure, puis passer le câble
  dans le presse-étoupe avant de souder (la fiche XLR ne passe pas dedans).

## 4. Rubans LED (carte entière) — TBTS

| Bornier | Sérigraphie | Raccorder |
|---------|-------------|-----------|
| **J5** | `+` / `−` | Sortie de l'alimentation LED 12 ou 24 V : **+ sur « + », − sur « − »** |
| **J6** | `V+`, `1` | V+ commun des rubans (anode commune), canal 1 |
| **J8** | `2`, `3`, `4` | Canaux 2, 3, 4 |

- 🔴 Alimentation LED **certifiée à sortie isolée TBTS** (ES-08), alimentée elle-même par
  la sortie J7 du nœud (elle s'éteint avec le relais) ou par une prise séparée.
- Rubans à **anode commune** (V+ commun, retour de chaque couleur commuté vers la masse) :
  RGB, RGBW ou quatre rubans monochromes.
- **Polarité de J5** : une inversion fait chauffer la diode de protection D3 sans
  forcément faire fondre F2 (alimentation limitée en courant). Vérifier au multimètre
  avant de brancher.
- Courant : **6 A par canal** maximum, **16 A au total** en continu (F2 = 20 A). Section
  des fils : 1,5 mm² jusqu'à 10 A, 2,5 mm² au-delà (V+ et J5 portent le courant total)
[À valider : règle de choix pour des longueurs courtes dans le boîtier, à confirmer
selon la longueur réelle des câbles et la chute de tension admise].
- Les deux câbles (alimentation, rubans) passent par les presse-étoupes M16 de la partie
  rubans.

## 5. Affectation DMX (rappel)

À partir de `start_address` (réglé à l'enrôlement, [mise-en-service.md](mise-en-service.md)) :

| Canal | Carte cassée | Carte entière, 8 bits (`pwm_mode=0`) | Carte entière, 16 bits (`pwm_mode=1`) |
|-------|--------------|--------------------------------------|---------------------------------------|
| `start_address` | Relais (≥ 128 = allumé) | Relais | Relais |
| +1 … +4 | — | Rubans 1 à 4 | Ruban 1 MSB, LSB, ruban 2 MSB, LSB… (+1 … +8) |

Si `relay_dmx=0`, le relais ne suit plus le DMX et les rubans commencent à
`start_address`. La ligne DMX filaire recopie **tout l'univers** : le projecteur garde
sa propre adresse, réglée sur le projecteur, qui ne doit pas chevaucher celles du nœud.
