# Révision suivante de la carte (v0.4)

Idées et corrections à intégrer à la prochaine révision du PCB. Une ligne par point,
avec sa source. Rien de tout cela ne concerne la carte v0.3 déjà fabriquée.

## Programmation et console

### Connecteur USB-C pour flasher sans adaptateur

Demandé le 2026-10-13. Aujourd'hui, le flash et la console passent par les pastilles J3,
avec un câble USB soudé ou un adaptateur ([docs/flash.md](../docs/flash.md)).

- **Pas besoin de convertisseur USB-TTL** (CH340, CP2102) : l'ESP32-C3 a un USB natif
  (USB Serial/JTAG) sur IO18 (D−) et IO19 (D+), déjà sortis sur J3. Le connecteur
  USB-C se câble directement sur ces lignes, et le passage en mode flash est
  automatique.
- Résistances de 5,1 kΩ sur CC1 et CC2 vers la masse, sinon un chargeur ou un câble
  USB-C vers USB-C ne fournit pas le 5 V.
- Protection ESD sur D+/D− et VBUS (par exemple USBLC6-2SC6), au plus près du
  connecteur.
- Le 5 V du connecteur arrive sur l'entrée de U3, comme J3-5V aujourd'hui. Il faut une
  diode Schottky (ou une diode idéale) entre VBUS et le rail +5V, pour ne jamais
  renvoyer le 5 V USB dans la sortie de PS1, ni celui de PS1 dans le PC.
- Placement : côté basse tension, en bord de carte, loin de la zone 230 V et à plus de
  15 mm de l'antenne de U1. Garder les pastilles J3 en plus, pour le banc.
- 🔴 **Relecture humaine obligatoire** : un connecteur USB-C accessible sur une carte
  raccordée au secteur. La règle reste de flasher hors secteur
  ([docs/securite.md](../docs/securite.md), règle 2). À décider : connecteur accessible
  seulement boîtier ouvert (couvercle basse tension retiré), ou au travers d'une paroi
  avec un bouchon. Dans le second cas, revoir l'isolement entre la masse USB et le 230 V
  (elle est isolée par PS1, mais le boîtier ne doit pas permettre de brancher un PC
  pendant que J1 est sous tension sans que ce soit voulu).
- Le boîtier (`enclosure/enclosure.py`) doit suivre : découpe ou accès selon le choix
  ci-dessus.
