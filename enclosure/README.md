# Boîtier dmxnow (livrable 8.6)

🔴 **RELECTURE HUMAINE OBLIGATOIRE** : cloison 230 V, accès aux borniers, matériau
(SPEC §4.12, ES-05).

Modèle CadQuery paramétrique (`enclosure.py`), deux variantes :

| Variante | Carte | Encombrement hors tout (parois + bossages + oreilles) | Corps seul |
|----------|-------|--------------------------------------------------------|------------|
| `full` | carte entière (146 × 65,5 mm) | 208 × 88 × 40 mm | 208 × 72 × 40 mm |
| `cut` | partie principale seule (carte cassée) | 150 × 88 × 40 mm | 145 × 72 × 40 mm |

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
| `base` | 1 | fond sur le plateau | Fond, parois, cloison 230 V / TBT, supports du PCB, presse-étoupes, clip du WAGO 221-413, passants de colliers |
| `lid` | 1 | face lisse sur le plateau | 🔴 Couvercle unique, vissé (outil requis pour atteindre les borniers secteur) ; jupe de cloison au-dessus du PCB ; guide du poussoir SW1 ; aérations au-dessus des MOSFET (`full`) |
| `lid_light_pipe` | (1) | idem | Variante de `lid` avec le logement du guide de lumière Ø 3 mm au-dessus de D4 (option A7) |
| `sw1_plunger` + `sw1_collar` | 1 + 1 | debout | Poussoir captif de SW1 (A6) : le collier se colle ou s'emmanche sous le tube de guidage |

## Achats

| Article | `full` | `cut` | Note |
|---------|--------|-------|------|
| Presse-étoupe M16 × 1,5 plastique + contre-écrou (serrage 4,5 à 10 mm) | 5 | 3 | Secteur ×3 (H05VV-F 3G1,5 ≈ 8 à 9 mm), rubans ×1, alimentation LED ×1 [V-ENC-01] |
| Presse-étoupe M12 × 1,5 plastique + contre-écrou (serrage jusqu'à 7 mm) | 1 | 1 | Queue DMX (câbles DMX souvent 6 à 6,5 mm, au-delà du PG7) [V-ENC-01] |
| Insert fileté M3 à chaud, Ø 4,0 × 5,7 mm | 10 | 9 | 8 couvercle, 1 ou 2 PCB |
| Vis M3 × 6 tête cylindrique | 8 | 8 | Couvercle (lamage de 1,2 mm) |
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

1. Inserts à chaud dans les bossages (couvercle) et les plots H2/H3.
2. Clipser le WAGO 221-413 dans son logement (chambre de gauche).
3. Poser le PCB : l'ergot imprimé traverse H1, les languettes de la cloison entrent dans
   les fentes d'isolement ; visser H2 (et H3 sur la carte entière).
4. Presse-étoupes : écrous tournés méplat contre méplat (les trois écrous secteur sont
   espacés de 21,5 mm pour 22 mm sur angles).
5. Câbles secteur : gaine serrée par le presse-étoupe (seul arrêt de traction) ; PE
   au 221-413 d'abord, puis L et N aux WAGO 2604 ; conducteurs sans tension mécanique.
6. Poussoir SW1 : glisser le poussoir dans le tube par-dessous, emmancher le collier.
7. Poser le couvercle : la jupe descend entre K1/PS1 et la cloison sans forcer, l'encoche
   du rebord de centrage passe au-dessus de la cloison côté bande F1. Visser les 8 vis.

## Choix de conception (justifications)

- **Chambres de câblage** : un contre-écrou de presse-étoupe M16 (22 mm sur angles) ne peut
  pas traverser le plan du PCB ; les WAGO étant en bord de carte, les presse-étoupes sont
  dans des chambres aux extrémités. Côté secteur, la chambre (34 mm) contient l'écrou,
  8 mm libres pour plier les câbles (ancien étrier, supprimé le 2026-10-15 : il gênait) et la zone d'épanouissement des conducteurs avec le 221-413 (A9).
- **Cloison 230 V / TBT** 🔴 : une cloison continue du fond au couvercle est impossible sur
  la ligne X = 49 mm, que K1 et PS1 enjambent. Elle est réalisée en trois parties :
  (1) paroi du fond, pleine hauteur hors carte (bande de F1) et sous la carte ailleurs ;
  (2) languettes de 0,8 mm qui remplissent les fentes d'isolement du PCB ; (3) jupe du
  couvercle au-dessus de la carte, qui descend à 0,5 mm du PCB et passe à 0,5 mm
  au-dessus de K1 et PS1 (leurs boîtiers assurent l'isolement à cet endroit).
- **Un seul couvercle** (2026-10-13, auparavant un couvercle 230 V et un couvercle TBT) :
  ES-05 demande seulement que les borniers secteur soient sous un couvercle vissé ; un
  couvercle unique le respecte, avec une pièce et des vis en moins. Le rebord de centrage
  porte une encoche au-dessus de la cloison (il appuyait dessus sur la maquette PLA et
  empêchait la fermeture) ; `make check` vérifie désormais que couvercle et fond ne se
  touchent pas.
- **H1 sans métal** : H1 est à 13,5 mm de la zone d'antenne ; il reçoit un ergot imprimé
  et un tube presseur du couvercle au lieu d'un insert (SPEC : rien de métallique à moins
  de 15 mm de l'antenne). Pour la même raison, la variante `cut` n'a pas de vis dans le
  coin supérieur droit.
- **Points d'appui** : plots sous le PCB et presseurs du couvercle aux points calculés
  par `export_board.py` (≥ 3 mm des pastilles, ≥ 2,5 mm des composants).
- **Aérations** (R-08) : fentes dans le couvercle au-dessus de Q2 à Q5 et entrées
  basses dans la paroi, sous la partie sécable. Aucune ouverture au-dessus de la zone 230 V.
- **DMX en M12** plutôt que PG7 : plage de serrage jusqu'à 7 mm (câbles DMX 6 à 6,5 mm).

## Écarts et points à valider

| Point | État |
|-------|------|
| ENF-05 (≤ 150 × 65 × 45 / ≤ 110 × 65 × 45) | **Non tenu** : 208 × 72 × 40 (corps, `full`), 145 × 72 × 40 (`cut`). Longueur : chambres de presse-étoupes. Largeur : bande de F1 (carte de 65,5 mm) + parois. Hauteur tenue. |
| Hauteurs de F2 avec fusible (27 mm, mesurée le 2026-10-15 : le couvercle ne fermait pas avec 21 mm estimés), C7 (17,5 mm), RV1 (16 mm) | F2 mesurée ; C7 et RV1 à mesurer [V-ENC-03] |
| Arrêt de traction des câbles secteur par le presse-étoupe seul (étrier supprimé le 2026-10-15) | Relecture humaine 🔴 : presse-étoupe à joint serrant, essai de traction |
| Presse-étoupes : diamètres de câbles, plages de serrage, dimensions des contre-écrous | [V-ENC-01] |
| Filament V-0, épaisseur certifiée | [V-ENC-02] 🔴 |
| Jupe de cloison au-dessus de K1 / PS1 (0,5 mm) : suffisante avec les boîtiers des composants ? | Relecture humaine 🔴 |
| Tenue du PCB : 1 vis (H2) + ergot H1 + appuis ; la partie sécable (`full`) ajoute H3 | À éprouver sur prototype (effort de levier des WAGO) |

## Vérifications automatiques (`make check`)

- solides valides (`isValid()`) et fermés ;
- aucune intersection des pièces avec le PCB ni avec l'enveloppe des composants
  (empreinte × hauteur) ;
- aucune intersection entre le couvercle et le fond (le couvercle se ferme) ;
- carte + 0,5 mm contenue dans la cavité ;
- parois ≥ 2,5 mm, fond et couvercle ≥ 2,0 mm ;
- contre-écrous des presse-étoupes : hors du PCB, des composants, dans la hauteur ;
  ouverture en goutte d'eau couverte par l'écrou ;
- aucun métal (inserts, vis) à moins de 15 mm de la zone d'antenne.

## Boîtier du dongle (`dongle_case.py`)

Boîtier de la **Seeed XIAO ESP32-C3** (référence 113991054) avec une **antenne dipôle
vissée** sur une embase RP-SMA, retenu à la place d'une clé USB-A toute faite pour garder
une antenne externe (SPEC 4.10). Encombrement : **59 × 39 × 13 mm**, oreilles comprises
(corps 48 × 25 × 13 mm).

Achats (Kiwi Electronics, 2026-09-27) :

| Article | Code | Note |
|---------|------|------|
| Seeed XIAO ESP32C3 | SS-113991054 | |
| Câble **RP-SMA** vers u.FL, 14 cm, embase à visser | KW-1518 | pas le « SMA to u.FL » : SMA et RP-SMA ne se connectent pas |
| Antenne dipôle 2,4 GHz **RP-SMA** 5 dBi | ANT-24GHZ-5DBI | rayonne surtout à l'horizontale : la tenir verticale |

| Pièce | Orientation | Rôle |
|-------|-------------|------|
| `out/dongle/tray` | fond sur le plateau | Ouverture USB-C avec lamage pour la fiche, nervures et butée du XIAO, trou Ø 6,6 mm de l'embase RP-SMA dans une paroi de 2,5 mm, place pour lover le câble, oreilles pour un collier |
| `out/dongle/lid` | face gravée sur le plateau | Lèvre à clipser (échancrée au-dessus de l'embase), deux appuis sur les bords du PCB |

- **Matériau** : PETG ou PLA (5 V USB seulement, pas de secteur : pas d'exigence V-0).
- **Montage** : XIAO poussé contre la paroi USB-C ; embase RP-SMA passée de l'intérieur
  dans la paroi opposée, rondelle et écrou à l'extérieur ; câble clipsé sur le
  connecteur U.FL du XIAO, lové en une boucle d'au moins 18 mm de diamètre ; couvercle
  clipsé ; antenne vissée à la main.
- **Utilisation** : câble USB-C vers USB-A sur le Pi, avec une rallonge ; dongle suspendu
  par son câble USB (ou par un collier dans une oreille), antenne vers le bas, verticale.
- **Flash** : par l'USB-C, sans ouvrir le boîtier (l'USB Serial/JTAG de l'ESP32-C3 passe
  en mode téléchargement tout seul) ; les boutons BOOT et RESET ne sont pas accessibles.

Cotes à confirmer sur les pièces reçues [V-ENC-04] : épaisseur du PCB (1,2 mm prévu),
dépassement de l'USB-C au-delà du bord (1,0 mm prévu), hauteur des composants
(3,4 mm prévu), corps de l'embase RP-SMA côté intérieur (Ø 9,4 × 9 mm prévu), filetage
1/4"-36 (trou Ø 6,6 mm). Ce sont des paramètres en tête de `dongle_case.py`.
