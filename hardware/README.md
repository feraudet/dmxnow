# dmxnow — matériel

PCB du nœud : 2 couches, cuivre 2 oz, **146 × 54 mm** plus une bande de 47,5 × 11,5 mm
au-dessus de la zone 230 V (porte-fusible F1), séparation à X = 100 mm par fente fraisée
et trois languettes perforées (partie principale « projecteur » 100 × 54 mm, partie
sécable « rubans » 46 × 54 mm). Révision 0.3 (après revue de conception, voir
`REVIEW.md`).

> 🔴 Carte manipulant du 230 V : lire et compléter [REVIEW.md](REVIEW.md) avant toute
> commande ou mise sous tension. Les cotes de K1 (Omron G5RL-1A-E-HR), des borniers WAGO
> 2604 et de PS1 (Mean Well IRM-03-5) ont été relevées sur les fiches constructeur
> ([datasheets/README.md](datasheets/README.md)) ; leur contrôle fait partie de la relecture.

## Contenu

| Fichier | Rôle |
|---------|------|
| `gen/design.py` | **Source unique** : composants, empreintes, broches → nets, classes de nets |
| `gen/footprints.py` | Empreintes du projet (`lib/dmxnow.pretty`), cotes et sources dans `DIMS` |
| `gen/sch.py` | Génère `dmxnow.kicad_sch` (schéma à étiquettes, symboles embarqués) |
| `gen/project.py` | Génère `dmxnow.kicad_pro` (classes de nets) et `dmxnow.kicad_dru` (règles 230 V) |
| `gen/pcb.py` | Génère `dmxnow.kicad_pcb` : contour, fentes, languettes perforées, placement, routage 230 V et LED, plans |
| `gen/route.py` | Routage des signaux basse tension par Freerouting, vias d'échappement et de couture GND |
| `gen/fixup.py` | Passe de finition : ferme les liaisons laissées par le routeur (segments directs, vias vers les plans) |
| `gen/vendor.py` | Copie figée des symboles et empreintes KiCad utilisés (`lib/vendor/`) |
| `gen/check.py` | Contrôles de cohérence : netlist du schéma, pastilles du PCB, traversée de la découpe |
| `gen/drc.py` | DRC local via l'API pcbnew (KiCad 7+) |
| `gen/fab.py` | Sorties JLCPCB dans `fab/` |
| `lib/` | Bibliothèques : `dmxnow.pretty`, `Espressif.*` (espressif/kicad-libraries, CC-BY-SA 4.0) |
| `REVIEW.md` | Liste de contrôle de la relecture humaine |

Ne pas éditer les fichiers KiCad à la main : modifier les scripts et régénérer (un
changement manuel serait écrasé et rendrait la CI rouge).

## Régénérer

Prérequis : KiCad ≥ 7 (module Python `pcbnew`, `kicad-cli`), Java ≥ 17, Freerouting
(`FREEROUTING_JAR`, défaut `/opt/freerouting/freerouting.jar`).

```sh
cd hardware
make lib sch project   # empreintes, schéma, projet et règles
make pcb route         # PCB puis routage automatique + finition (~15 min)
make check             # netlist, cohérence PCB, DRC local
make fab               # Gerbers, perçages, BOM/CPL JLCPCB
```

`make pcb` repart de zéro : il faut relancer `make route` ensuite (ou `make reimport`
pour réappliquer la dernière session Freerouting si aucun composant n'a bougé).
Freerouting n'est pas déterministe : deux passages donnent des routages différents,
toujours validés par `make check`.

## Contrôles

- **Local** (KiCad 7) : `make check` (netlist schéma = `design.py`, pastilles PCB =
  `design.py`, seuls PWM1-4, BOARD_SENSE, +5V, GND traversent la découpe et uniquement
  sur les languettes, aucune piste 230 V au-delà de X = 46 mm, aucun via dans une
  pastille CMS, DRC, puis `gen/drc_canary.py` : des défauts injectés doivent déclencher
  chaque règle 230 V, preuve que les règles personnalisées sont chargées).
- **CI** (`.github/workflows/hardware.yml`, KiCad 9) : fichiers générés à jour, ERC, DRC
  avec parité schéma/PCB, sorties de fabrication, rendus 3D dessus/dessous (artefact
  `dmxnow-hardware`).

## Règles d'isolement (🔴)

Définies dans `gen/project.py` → `dmxnow.kicad_dru` :

| Règle | Valeur |
|-------|--------|
| Cuivre 230 V ↔ tout autre cuivre ou trou | ≥ 6 mm |
| Entre nets 230 V | ≥ 3 mm |
| Pastilles internes de K1 (COM/NO) et de PS1 (AC) | ≥ 2 mm (imposé par le composant) |
| Cuivre 230 V ↔ bord de carte | ≥ 1 mm |

Géométrie : cuivre 230 V à X ≤ 46 mm, basse tension à X ≥ 52 mm, fentes de 1,2 mm à
X = 49 mm sous K1 et PS1, aucun cuivre à moins de 6 mm de la pastille NC de PS1 (rangée
AC du module). Aucun trou de fixation dans la zone 230 V. Le PE ne passe pas
par la carte (WAGO 221-413 dans le boîtier, arbitrage A9).

## Commande JLCPCB

- `fab/dmxnow-gerbers.zip` : 2 couches, 1,6 mm, **2 oz**, FR-4 TG ≥ 150.
- Séparation : fente et perforations sont dans les Gerbers (Edge.Cuts, NPTH). JLCPCB
  compte la carte comme **2 designs** : « Different Design = 2 », « Panel by Customer »
  1×1, « Remove order number = Yes ». Remarque de commande :
  « One circuit with an internal routed slot and 3 breakaway tabs carrying traces; deliver and assemble as one piece, do NOT separate. SMT: convey on the straight short edges X=0 and X=146; U1/Q5/R10 are close to the Y=54 edge by design. J6, J3, J2 not populated: keep holes open (no solder fill). J1, J4, J7, J5: wire entry toward board edge. RV1: form leads to the PCB holes. F2: press flat before soldering. F1/F2 fuses are not fitted. »
- Assemblage complet (CMS + traversants, PCBA « Standard ») : `fab/bom_jlcpcb_full.csv`
  + `fab/cpl_jlcpcb_full.csv` ; CMS seuls (PCBA « Economic », traversants à la main) :
  `*_smt.csv`. Suffixe `_led` : avec la LED d'état (option A7). Positions et rotations
  converties aux conventions JLCPCB (`gen/fab.py`, `JLC_FIX`) ; contrôler l'aperçu de
  placement à la commande. Références LCSC vérifiées le 2026-09-26 (WAGO 2604-1105 arrêté
  chez WAGO, exclu de la BOM JLC). La cartouche de F1 (Littelfuse 0215.500MXP) et le fusible de F2
  sont à insérer à la main.
- Composants traversants et hors carte : `fab/bom_full.csv`.
