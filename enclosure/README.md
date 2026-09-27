# Boîtier dmxnow (livrable 8.6)

🔴 **RELECTURE HUMAINE OBLIGATOIRE** : cloison 230 V, accès aux borniers, matériau
(SPEC §4.12, ES-05).

Modèle CadQuery paramétrique (`enclosure.py`), deux variantes :

| Variante | Carte | Encombrement hors tout (parois + bossages + oreilles) | Corps seul |
|----------|-------|--------------------------------------------------------|------------|
| `full` | carte entière (146 × 65,5 mm) | 208 × 88 × 34 mm | 208 × 72 × 34 mm |
| `cut` | partie principale seule (carte cassée) | 150 × 88 × 34 mm | 145 × 72 × 34 mm |

L'objectif ENF-05 (≤ 150 × 65 × 45 mm entière, ≤ 110 × 65 × 45 mm cassée) **n'est pas
tenu en longueur ni en largeur**, voir « Écarts » ci-dessous.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `board.json` | Géométrie de la carte (contour, fentes, trous, encombrement et hauteur de chaque composant, points d'appui), **générée** par `hardware/gen/export_board.py` |
| `enclosure.py` | Modèle, vérifications (SPEC §8.6), exports |
| `render.py` | Rendus PNG assemblés (fermé, ouvert) |
| `out/<variante>/*.step` | Pièces en position d'assemblage (CAO) |
| `out/<variante>/*.stl` | Pièces en position d'impression (trancheur) |
| `out/<variante>/assembly_*.png` | Rendus |

```
pip install -r requirements.txt       # CadQuery 2.8
make                                  # vérifie, exporte les deux variantes, rend les PNG
make check                            # vérifications seules
```

Après toute modification du PCB : `cd hardware/gen && python3 export_board.py`, puis
`make` ici.

## Pièces imprimées

| Pièce | Qté | Orientation | Rôle |
|-------|-----|-------------|------|
| `base` | 1 | fond sur le plateau | Fond, parois, cloison 230 V / TBT, supports du PCB, presse-étoupes, sellette de l'étrier, clip du WAGO 221-413, passants de colliers |
| `cover_230v` | 1 | face lisse sur le plateau | 🔴 Couvercle d'accès aux borniers secteur (J1, J4, J7, jonction PE), vissé ; jupe de cloison au-dessus du PCB ; recouvre le bord du couvercle TBT |
| `lid_lv` | 1 | face lisse sur le plateau | Couvercle basse tension, vissé ; guide du poussoir SW1 ; aérations au-dessus des MOSFET (`full`) |
| `lid_lv_light_pipe` | (1) | idem | Variante de `lid_lv` avec le logement du guide de lumière Ø 3 mm au-dessus de D4 (option A7) |
| `clamp_bar` | 3 | rainure sur le plateau | Barres d'étrier (arrêt de traction indépendant du presse-étoupe, ES-05) |
| `sw1_plunger` + `sw1_collar` | 1 + 1 | debout | Poussoir captif de SW1 (A6) : le collier se colle ou s'emmanche sous le tube de guidage |

## Achats

| Article | `full` | `cut` | Note |
|---------|--------|-------|------|
| Presse-étoupe M16 × 1,5 plastique + contre-écrou (serrage 4,5 à 10 mm) | 5 | 3 | Secteur ×3 (H05VV-F 3G1,5 ≈ 8 à 9 mm), rubans ×1, alimentation LED ×1 [V-ENC-01] |
| Presse-étoupe M12 × 1,5 plastique + contre-écrou (serrage jusqu'à 7 mm) | 1 | 1 | Queue DMX (câbles DMX souvent 6 à 6,5 mm, au-delà du PG7) [V-ENC-01] |
| Insert fileté M3 à chaud, Ø 4,0 × 5,7 mm | 16 | 15 | 8 couvercles, 6 étriers, 1 ou 2 PCB |
| Vis M3 × 6 tête cylindrique | 8 | 8 | Couvercles (lamage de 1,2 mm) |
| Vis M3 × 16 | 6 | 6 | Barres d'étrier (pas plus long : la vis toucherait le fond de l'insert avant de serrer) |
| Vis M3 × 6 + rondelle isolante | 2 | 1 | PCB (H2, H3) |
| WAGO 221-413 | 1 | 1 | Jonction des trois PE (A9) |
| Guide de lumière Ø 3 mm (PMMA) | option | option | A7 |
| Filament **ABS-FR ou PC-ABS-FR UL94 V-0** | ~150 g | ~115 g | Pièces pleines (masse volumique 1,2) [V-ENC-02] 🔴 |

## Impression

- Matériau **UL94 V-0 (au minimum V-1)** : PETG et ABS standard (HB) interdits pour une
  enveloppe contenant du secteur (SPEC §4.12). Conserver la fiche technique du filament
  et l'épaisseur à laquelle le classement est donné ; l'épaisseur des parois (2,5 mm) doit
  être au moins égale à celle-ci [V-ENC-02].
- Parois pleines : **100 % de remplissage** (ou périmètres suffisants pour remplir les 2,5 mm).
- Imprimante fermée, buse 240 à 260 °C, plateau 100 °C (ABS-FR) ; bordure (« brim ») sur
  le fond (R-15).
- Aucun support nécessaire : trous horizontaux en goutte d'eau tronquée, porte-à-faux ≤ 45°.

## Montage

1. Inserts à chaud dans les bossages (couvercles), la sellette (étriers) et les plots H2/H3.
2. Clipser le WAGO 221-413 dans son logement (chambre de gauche).
3. Poser le PCB : l'ergot imprimé traverse H1, les languettes de la cloison entrent dans
   les fentes d'isolement ; visser H2 (et H3 sur la carte entière).
4. Presse-étoupes : écrous tournés méplat contre méplat (les trois écrous secteur sont
   espacés de 21,5 mm pour 22 mm sur angles).
5. Câbles secteur : gaine serrée par le presse-étoupe **et** par la barre d'étrier ; PE
   au 221-413 d'abord, puis L et N aux WAGO 2604 ; conducteurs sans tension mécanique.
6. Poussoir SW1 : glisser le poussoir dans le tube par-dessous, emmancher le collier.
7. Visser le couvercle TBT, puis le couvercle 230 V (il recouvre le bord du couvercle TBT).

## Choix de conception (justifications)

- **Chambres de câblage** : un contre-écrou de presse-étoupe M16 (22 mm sur angles) ne peut
  pas traverser le plan du PCB ; les WAGO étant en bord de carte, les presse-étoupes sont
  dans des chambres aux extrémités. Côté secteur, la chambre (34 mm) contient l'écrou,
  l'étrier (ES-05) et la zone d'épanouissement des conducteurs avec le 221-413 (A9).
- **Cloison 230 V / TBT** 🔴 : une cloison continue du fond au couvercle est impossible sur
  la ligne X = 49 mm, que K1 et PS1 enjambent. Elle est réalisée en trois parties :
  (1) paroi du fond, pleine hauteur hors carte (bande de F1) et sous la carte ailleurs ;
  (2) languettes de 0,8 mm qui remplissent les fentes d'isolement du PCB ; (3) jupe du
  couvercle 230 V au-dessus de la carte, qui descend à 0,5 mm du PCB et passe à 0,5 mm
  au-dessus de K1 et PS1 (leurs boîtiers assurent l'isolement à cet endroit). Le couvercle
  230 V recouvre le bord du couvercle TBT (« lèvre »).
- **H1 sans métal** : H1 est à 13,5 mm de la zone d'antenne ; il reçoit un ergot imprimé
  et un tube presseur du couvercle au lieu d'un insert (SPEC : rien de métallique à moins
  de 15 mm de l'antenne). Pour la même raison, la variante `cut` n'a pas de vis dans le
  coin supérieur droit.
- **Points d'appui** : plots sous le PCB et presseurs des couvercles aux points calculés
  par `export_board.py` (≥ 3 mm des pastilles, ≥ 2,5 mm des composants).
- **Aérations** (R-08) : fentes dans le couvercle TBT au-dessus de Q2 à Q5 et entrées
  basses dans la paroi, sous la partie sécable. Aucune ouverture dans le couvercle 230 V.
- **DMX en M12** plutôt que PG7 : plage de serrage jusqu'à 7 mm (câbles DMX 6 à 6,5 mm).

## Écarts et points à valider

| Point | État |
|-------|------|
| ENF-05 (≤ 150 × 65 × 45 / ≤ 110 × 65 × 45) | **Non tenu** : 208 × 72 × 34 (corps, `full`), 145 × 72 × 34 (`cut`). Longueur : chambres de presse-étoupes + étriers (ES-05). Largeur : bande de F1 (carte de 65,5 mm) + parois. Hauteur tenue. |
| Hauteurs de F2 avec fusible (21 mm), C7 (17,5 mm), RV1 (16 mm) | Estimées, à mesurer sur les pièces [V-ENC-03] |
| Presse-étoupes : diamètres de câbles, plages de serrage, dimensions des contre-écrous | [V-ENC-01] |
| Filament V-0, épaisseur certifiée | [V-ENC-02] 🔴 |
| Jupe de cloison au-dessus de K1 / PS1 (0,5 mm) : suffisante avec les boîtiers des composants ? | Relecture humaine 🔴 |
| Tenue du PCB : 1 vis (H2) + ergot H1 + appuis ; la partie sécable (`full`) ajoute H3 | À éprouver sur prototype (effort de levier des WAGO) |

## Vérifications automatiques (`make check`)

- solides valides (`isValid()`) et fermés ;
- aucune intersection des pièces avec le PCB ni avec l'enveloppe des composants
  (empreinte × hauteur) ;
- carte + 0,5 mm contenue dans la cavité ;
- parois ≥ 2,5 mm, fond et couvercles ≥ 2,0 mm ;
- contre-écrous des presse-étoupes : hors du PCB, des composants, dans la hauteur ;
  ouverture en goutte d'eau couverte par l'écrou ;
- aucun métal (inserts, vis) à moins de 15 mm de la zone d'antenne.

## Boîtier du dongle (`dongle_case.py`)

Boîtier de la **Seeed XIAO ESP32-C3** (référence 113991054) et de son antenne FPC
2,4 GHz fournie (40 × 20 mm, câble de 80 mm), retenu à la place d'une clé USB-A toute
faite pour garder l'antenne externe (SPEC 4.10). Encombrement : **80 × 25 × 9 mm**,
languette d'accroche comprise.

| Pièce | Orientation | Rôle |
|-------|-------------|------|
| `out/dongle/tray` | fond sur le plateau | Ouverture USB-C avec lamage pour la fiche, nervures et butée du XIAO, rebord de l'antenne, languette pour collier ou sangle |
| `out/dongle/lid` | face gravée sur le plateau | Lèvre à clipser, deux appuis sur les bords du PCB |

- **Matériau** : PETG ou PLA (5 V USB seulement, pas de secteur : pas d'exigence V-0).
- **Montage** : XIAO poussé contre la paroi USB-C ; câble de l'antenne clipsé sur le
  connecteur U.FL ; antenne collée par son adhésif dans son rebord, à 7 mm de la carte
  (loin du plan de masse) ; câble coaxial lové dans l'espace libre ; couvercle clipsé.
- **Utilisation** : câble USB-C vers USB-A sur le Pi, avec une rallonge pour pendre le
  dongle en hauteur par sa languette, antenne verticale de préférence.
- **Flash** : par l'USB-C, sans ouvrir le boîtier (l'USB Serial/JTAG de l'ESP32-C3 passe
  en mode téléchargement tout seul) ; les boutons BOOT et RESET ne sont pas accessibles.

Cotes à confirmer sur une carte reçue [V-ENC-04] : épaisseur du PCB (1,2 mm prévu),
dépassement de l'USB-C au-delà du bord (1,0 mm prévu), hauteur des composants
(3,4 mm prévu). Elles sont des paramètres en tête de `dongle_case.py`.
