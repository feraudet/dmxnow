# Sécurité

🔴 **RELECTURE HUMAINE OBLIGATOIRE** — ce document engage la sécurité des personnes. Il
doit être relu et validé par une personne qualifiée en électricité avant toute mise sous
tension. Les exigences de référence sont dans [SPEC §2.3](../spec/SPEC.md) (ES-01 à ES-08).

## 1. Ce qui est dangereux

Le nœud dmxnow est raccordé au **secteur 230 V** et commute le projecteur par un relais.

| Zone | Tension | Accessible ? |
|------|---------|--------------|
| Borniers J1, J4, J7, relais K1, fusible F1, varistance RV1, entrée de PS1 (moitié gauche de la carte, sous le **couvercle orange**) | **230 V AC** | Non : couvercle vissé, outil requis |
| Basse tension : ESP32, DMX, bouton SW1, pastilles J3 (sous le couvercle bleu) | 5 V / 3,3 V, isolés du secteur par PS1 | Queue DMX uniquement |
| Partie rubans : J5, J6, J8, F2 (carte entière) | 12 ou 24 V DC (TBTS) | Borniers sous le couvercle bleu |

L'isolement entre secteur et basse tension repose sur : l'alimentation isolée PS1
(Mean Well IRM-03), 6 mm de distance sur la carte, des fentes fraisées, la cloison du
boîtier. **Un seul défaut** (carte endommagée, conducteur mal dénudé, humidité, boîtier
fondu) peut rendre la queue DMX ou les rubans dangereux.

## 2. Règles

1. **Jamais de travail sous tension.** Débrancher la fiche secteur (pas seulement couper
   le relais) avant d'ouvrir un couvercle. Le relais ne coupe que la **phase** des sorties :
   le neutre, les borniers d'entrée, F1 et PS1 restent sous tension.
2. **Jamais de programmation ni de mesure avec le secteur raccordé** (ES-07). Le flash par
   J3 se fait carte hors secteur, alimentée par **J3-5V** (jamais J3-3V3).
3. **Terre (PE)** : les trois PE (entrée, deux sorties) se rejoignent dans le WAGO 221-413
   du compartiment 230 V. Le PE ne passe pas par la carte et n'est jamais coupé (ES-03).
4. **Protection amont** : prise protégée par un disjoncteur **≤ 16 A** et un différentiel
   **30 mA**. La carte n'a pas de fusible sur le chemin de puissance : son cuivre est
   dimensionné pour être protégé par le disjoncteur (A2).
5. **Charges** : 16 A maximum par nœud au total (J4 + J7). Recommandé : **un projecteur
   par nœud** (courant d'appel des alimentations à découpage, V-SYS-01). Rubans : 16 A
   maximum en continu, alimentation **certifiée à sortie isolée TBTS** (ES-08).
6. **Fusibles** : F1 = **T500 mA H 250 V céramique 5×20** uniquement (pouvoir de coupure
   1500 A) ; F2 = ATO **20 A**. Jamais de fusible plus gros, jamais de pontage.
7. **Boîtier** : imprimé en matériau **UL94 V-0** (ABS-FR ou PC-ABS-FR), parois pleines.
   PLA, PETG et ABS standard sont interdits pour le boîtier du nœud (le boîtier du dongle,
   sans secteur, peut être en PETG).
8. **Câbles** : chaque câble secteur passe par son presse-étoupe **et** sa barre d'étrier
   serrée ; aucun conducteur ne doit pouvoir être tiré jusqu'aux borniers.
9. **Environnement** : intérieur, sec. Le boîtier n'est pas étanche (aérations).

## 3. Essais du premier prototype (personne équipée et qualifiée)

Avant toute utilisation d'une série, sur au moins un nœud (détail :
[hardware/REVIEW.md §6](../hardware/REVIEW.md)) :

1. inspection visuelle, continuité, absence de court-circuit L/N, L/TBT, N/TBT ;
2. **essai diélectrique** secteur ↔ basse tension (toutes broches TBT reliées) :
   3 kV AC ou 4,2 kV DC pendant 60 s, sans claquage ;
3. première mise sous tension derrière un **transformateur d'isolement** et un
   différentiel 30 mA, charge résistive ;
4. essai de charge 10 A pendant 1 h (relevé thermique), 16 A en courte durée ;
5. 1000 commutations d'une vraie alimentation LED (courant d'appel).

## 4. Liste de contrôle avant chaque mise sous tension

À faire pour **chaque nœud**, fiche secteur débranchée. Ne brancher que si **toutes** les
cases sont cochées.

**Carte et boîtier**
- [ ] Nœud issu d'une série dont le prototype a passé les essais du §3.
- [ ] Boîtier imprimé en filament V-0 (fiche du filament conservée), sans fissure ni
      déformation, cloison et languettes intactes.
- [ ] F1 = T500 mA céramique 5×20 en place ; F2 = 20 A (carte entière).
- [ ] Aucun fil, aucune vis, aucun débris dans le compartiment 230 V.
- [ ] Pastilles J3 libres : aucun câble de programmation raccordé.

**Câblage secteur** (couvercle orange ouvert)
- [ ] Entrée sur **J1** (IN), sorties sur **J4** et **J7** (OUT) — L et N à leur place
      (sérigraphie « L/N »), conducteurs de 1,5 mm² dénudés à la longueur WAGO (11 à 13 mm [À valider, fiche WAGO 2604]),
      aucun brin hors du bornier, leviers fermés.
- [ ] Les trois PE dans le **WAGO 221-413**, leviers fermés, aucun PE sur la carte.
- [ ] **Continuité du PE** mesurée entre la broche de terre de la fiche d'entrée et celle
      de chaque sortie (quelques centaines de mΩ au plus).
- [ ] Chaque câble serré par son presse-étoupe **et** sa barre d'étrier ; essai de
      traction à la main sans mouvement des conducteurs.
- [ ] Couvercle 230 V remis et **vissé** (4 vis).

**Basse tension** (couvercle bleu ouvert)
- [ ] Queue DMX soudée sur J2 (GND, B−, A+), sortie par son presse-étoupe.
- [ ] Carte entière : alimentation LED **certifiée TBTS à sortie isolée**, raccordée à
      **J5 en respectant « + » et « − »** ; rubans sur J6/J8 (V+ commun, canaux 1 à 4).
- [ ] Couvercle basse tension vissé.

**Installation**
- [ ] Prise protégée par un disjoncteur ≤ 16 A et un différentiel 30 mA.
- [ ] Charge du projecteur (et de l'alimentation LED) connue et dans les limites du §2.5.
- [ ] Le nœud n'est pas posé sur une surface chaude ni enfermé sans ventilation.

## 5. En cas de doute

Odeur, échauffement du boîtier, déclenchement du différentiel, fusible F1 fondu : débrancher,
ne pas remplacer F1 avant d'avoir trouvé la cause, ne pas remettre sous tension.
