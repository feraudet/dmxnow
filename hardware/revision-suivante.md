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

## Rubans LED

### Tous les types de rubans : 5 sorties PWM et une sortie pixels

Demandé le 2026-10-15. En v0.3, la partie rubans n'a que 4 sorties PWM (RGBW, ou moins de
couleurs) : elle ne pilote ni les rubans RGB+CCT à 5 canaux, ni les rubans adressables
(un essai d'un ruban WS2811 à 3 fils par la XLR a été écarté : le SP3485 en 3,3 V sort
environ 3 V, trop juste pour un WS2812B en 5 V).

Types de rubans visés :

| Famille | Exemples | Ce qu'il faut sur la carte |
|---------|----------|----------------------------|
| Analogique, 1 à 5 canaux | blanc seul, CCT, RGB, RGBW, RGB+CCT (RGBWW) | 5 sorties PWM à + commun (une de plus qu'en v0.3) |
| Adressable, 1 fil | WS2811, WS2812B, WS2813, WS2815, SK6812 (RGBW), WS2814 (RGBW), TM1814, UCS1903 | une sortie DATA en 5 V |
| Adressable, 2 fils | APA102, SK9822, WS2801 | une sortie DATA et une sortie CLOCK en 5 V |

Proposition :

- **Cinquième sortie PWM** : un MOSFET Q6 de plus (AOD2610E, comme Q2 à Q5) et un WAGO
  2604-1102 de plus. Commande sur **IO20** (libre en v0.3, U0RXD inutilisé), avec une
  résistance de rappel à la masse comme R15 à R18, pour que la sortie reste éteinte au
  démarrage. L'ESP32-C3 a 6 canaux LEDC : 5 sorties PWM restent possibles.
- **Sortie pixels** : DATA sur **IO2**, CLOCK sur **IO8**. Ces deux broches sont tirées au
  +3V3 au démarrage (strapping, R3) : elles restent hautes et fixes, sans front, donc le
  ruban ne reçoit rien de faux avant que le firmware démarre. Ne pas prendre IO21 : la ROM
  y écrit son message de démarrage (U0TXD), qui partirait dans le ruban.
- **Tampons 5 V** : les 4 portes du 74AHCT125 (U4) servent déjà aux PWM. Passer à un
  74AHCT244 (8 portes) ou ajouter un 74AHCT125 : 3 portes de plus (PWM5, DATA, CLOCK).
  Résistance de 33 Ω en série sur DATA et CLOCK, au plus près du connecteur, et une
  protection ESD sur les deux lignes.
- **Connecteur pixels** : WAGO 2604 à 3 pôles (DATA, CLOCK, GND_LED). Il ne porte pas le +
  du ruban : un ruban adressable de 10 m en 24 V tire environ 6 A, il est alimenté
  directement par son alimentation, dont le − rejoint GND_LED.
- **Firmware** :
  - un réglage `strip_type` : analogique 1 à 5 canaux, ou adressable (type de puce,
    nombre de pixels, ordre des couleurs, regroupement de pixels) ;
  - les pixels prennent leurs canaux dans l'univers du nœud, après ceux des sorties
    PWM : 3 ou 4 canaux par pixel, au plus 170 pixels RGB ou 128 RGBW par univers ;
  - 1 fil par le périphérique RMT, 2 fils par le SPI (GPSPI2, broches choisies par la
    matrice GPIO) ;
  - les conduites stockées sont limitées à 32 canaux : étendre le format, ou calculer
    l'effet dans le nœud, pour un feu le long du ruban.

Points à vérifier :

- La place sur la partie rubans (46 mm de large) pour 2 WAGO de plus, et le boîtier de la
  carte entière (`enclosure/enclosure.py`) : un presse-étoupe de plus, ou des câbles
  regroupés.
- Les rubans 5 V : vérifier que la partie rubans fonctionne avec VLED = 5 V (seuil de
  commande des AOD2610E, D3 et C7 sans effet).
- Le courant total sur J5 et la section des pistes avec 5 sorties PWM chargées.
- `spec/SPEC.md` et `docs/cablage.md` doivent suivre (nouvelle exigence, nouveaux
  borniers), avec une ADR pour le choix des broches.

## Secteur

### Terre (PE) sur la carte

Demandé le 2026-10-13. En v0.3, le PE ne passe pas par la carte : J1, J4 et J7 sont des
WAGO 2604 à 2 pôles (L, N), et les trois PE sont réunis par un WAGO 221-413 dans le
compartiment 230 V (arbitrage A9 de `spec/SPEC.md`). Câbler ce WAGO à part est une étape
de plus, et un oubli possible.

- Passer J1, J4 et J7 en **WAGO 2604 à 3 pôles** (L, N, PE), par exemple 2604-1103.
- Relier les trois PE par une piste ou un plan **dimensionné pour le courant de défaut**
  (au moins la section de L et N), sur les deux couches si besoin.
- Le PE reste dans la zone 230 V et garde les mêmes distances que L et N vis-à-vis de la
  basse tension (≥ 6 mm, `gen/project.py`). **Aucune liaison** entre le PE et la GND
  logique, DMX ou LED : l'isolement est assuré par PS1 (risque R-09).
- C'est ce routage qui avait été jugé infaisable proprement en 2 couches (A9). Options à
  étudier : PCB 4 couches, carte un peu plus haute dans la zone 230 V, ou borniers
  décalés pour libérer un couloir PE.
- Le boîtier (`enclosure/enclosure.py`) et `docs/cablage.md` doivent suivre (plus de
  WAGO 221-413).
- 🔴 **Relecture humaine obligatoire** : conducteur de protection d'une carte 230 V.
