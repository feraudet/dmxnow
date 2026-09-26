# dmxnow — matériel

PCB du nœud : 2 couches, cuivre 2 oz, **146 × 54 mm** entière, découpe V-cut à
X = 100 mm (partie principale « projecteur » 100 × 54 mm, partie sécable « rubans »
46 × 54 mm).

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
| `gen/pcb.py` | Génère `dmxnow.kicad_pcb` : contour, fentes, V-cut, placement, routage 230 V et LED, plans |
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
  `design.py`, seuls PWM1-4, BOARD_SENSE, +5V, GND traversent la découpe, aucune piste
  230 V au-delà de X = 46 mm, DRC).
- **CI** (`.github/workflows/hardware.yml`, KiCad 9) : fichiers générés à jour, ERC, DRC
  avec parité schéma/PCB, sorties de fabrication, rendus 3D dessus/dessous (artefact
  `dmxnow-hardware`).

## Règles d'isolement (🔴)

Définies dans `gen/project.py` → `dmxnow.kicad_dru` :

| Règle | Valeur |
|-------|--------|
| Cuivre 230 V ↔ tout autre cuivre ou trou | ≥ 6 mm |
| Entre nets 230 V | ≥ 3 mm |
| Pastilles internes d'un composant (K1 COM/NO, PS1 AC) | ≥ 2 mm (imposé par le composant) |
| Cuivre 230 V ↔ bord de carte | ≥ 1 mm |

Géométrie : cuivre 230 V à X ≤ 46 mm, basse tension à X ≥ 52 mm, fentes de 1 mm à
X = 49 mm sous K1 et PS1. Aucun trou de fixation dans la zone 230 V. Le PE ne passe pas
par la carte (WAGO 221-413 dans le boîtier, arbitrage A9).

## Commande JLCPCB

- `fab/dmxnow-gerbers.zip` : 2 couches, 1,6 mm, **2 oz**, FR-4 TG ≥ 150.
- V-cut : ligne dans `fab/dmxnow-vcut.gbr` (calque User.1) ; le préciser à la commande.
- Assemblage CMS : `fab/bom_jlcpcb_base.csv` + `fab/cpl_jlcpcb_base.csv`, ou variante
  `_led` avec la LED d'état (option A7). Références LCSC à revalider.
- Composants traversants et hors carte : `fab/bom_full.csv`.
