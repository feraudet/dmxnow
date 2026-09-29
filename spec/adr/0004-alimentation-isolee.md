# ADR 0004 : Alimentation interne isolée Mean Well IRM-03-5

**Statut :** Accepté. Décision 4 du cahier des charges, amendée par l'arbitrage A1 du 2026-09-25.

## Contexte

Le nœud doit être alimenté depuis le secteur et sa masse est reliée au DMX et aux rubans, donc accessible. La décision 4 retenait un Hi-Link HLK-PM05 ; les certifications des modules Hi-Link sont difficiles à vérifier et les contrefaçons fréquentes, ce qui pèse pour un projet publié et refabriqué par d'autres.

## Décision

Module AC/DC isolé **Mean Well IRM-03-5** (5 V, 600 mA, 3 W, homologué IEC/EN/UL 62368-1 selon le fabricant), protégé par F1 T500 mA et RV1 10D561K (à confirmer selon la fiche Mean Well). Le HLK-PM05 reste une empreinte de repli paramétrable, non retenue par défaut. Les alimentations non isolées sont exclues.

## Conséquences

- Masse DMX isolée du secteur : sécurité et absence de boucle secteur.
- Budget 5 V : ~200 mA moyen, ~420 mA crête pour 600 mA disponibles, marge ~30 % (SPEC §4.3).
- Coût +3,5 € par nœud environ : carte entière ≈ 47 €, en limite haute de la cible.
- Empreinte différente du HLK-PM05 : brochage et cotes à relever sur la fiche Mean Well (V-HW-09).

## Alternatives écartées

- Mean Well IRM-05-5 (1 A) : 45,7 × 25,4 × 21,5 mm, trop encombrant pour la zone 230 V et le boîtier (constaté au placement).

- HLK-PM05 (décision initiale) : moins cher, certification incertaine.
- Alimentations non isolées (type Shelly/Sonoff) : masse DMX au potentiel du secteur.
- Transformateur 50 Hz : volumineux.
