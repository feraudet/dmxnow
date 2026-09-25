# ADR 0004 — Alimentation interne isolée HLK-PM05

**Statut :** Accepté (décision 4) — réserve soumise à arbitrage A1

## Contexte

Le nœud doit être alimenté depuis le secteur et sa masse est reliée au DMX et aux rubans, donc accessible.

## Décision

Module AC/DC isolé Hi-Link HLK-PM05 (5 V, 600 mA), protégé par F1 T500 mA et RV1 10D561K. Les alimentations non isolées sont exclues.

## Conséquences

- Masse DMX isolée du secteur : sécurité et absence de boucle secteur.
- Budget 5 V : ~200 mA moyen, ~420 mA crête, marge ~30 % (SPEC §4.3).
- **Réserve (A1)** : certifications Hi-Link difficiles à vérifier, contrefaçons fréquentes. Alternative certifiée IEC/UL 62368-1 : Mean Well IRM-05-5 (+5 €). L'empreinte sera un paramètre du script de placement.

## Alternatives écartées

- Alimentations non isolées (type Shelly/Sonoff) : masse DMX au potentiel du secteur, exclu.
- Transformateur 50 Hz : volumineux.
- Mean Well IRM-05-5 : voir A1.
