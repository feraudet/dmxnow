# Conduites stockées

Un nœud peut garder en mémoire une **conduite** : une suite de couleurs et de valeurs
DMX qu'il joue en boucle, seul, dès qu'on le met sous tension. Pas besoin du Pi ni de
QLC+ pour qu'elle tourne. Exemple fourni : un feu de cheminée sur un ruban RGBW.

Détails techniques : [SPEC §4.13](../spec/SPEC.md), [PROTOCOL §10](../spec/PROTOCOL.md),
[ADR 0016](../spec/adr/0016-conduites-stockees.md).

## 1. Ce que fait le nœud

| Situation | Ce qui pilote les sorties |
|-----------|---------------------------|
| Mise sous tension, pas de DMX | La conduite, depuis le début |
| QLC+ envoie l'univers du nœud | QLC+, dès la première trame |
| QLC+ se tait depuis `resume_s` secondes (5 s par défaut) | La conduite, depuis le début |
| `dmxnow identify` | Le clignotement d'identification, puis retour à la situation d'avant |

La conduite pilote les **4 sorties rubans** et, si elle les contient, des **canaux de la
ligne DMX** (un projecteur branché sur la XLR). Les canaux qu'elle ne contient pas restent
à 0.

🔴 **Le relais ne suit jamais la conduite.** Il garde son état de mise sous tension. Si
l'alimentation des rubans est branchée sur une sortie 230 V du nœud (J4 ou J7), régler le
relais allumé au démarrage, sinon la conduite tourne sur un ruban sans courant :

```
dmxnow set node-2442B0 relay_power_on=1
```

Le ruban n'est pas adressable : toute sa longueur a la même couleur à un instant donné.
Le feu se fait dans le temps (scintillement, flambées, creux), pas le long du ruban.

## 2. Générer une conduite

Une conduite est un fichier `.dxs`, calculé à l'avance par un script Python. Les scripts
sont dans `shows/` ; ils n'ont besoin que de la bibliothèque `pi/dmxnow`.

```
PYTHONPATH=pi python3 shows/feu_de_cheminee.py
```

```
feu-cheminee: 4 channel(s) [+1, +2, +3, +4], 2995 keyframes, loop 300.3 s, resume after 5 s without DMX, 18010 bytes
written shows/feu-de-cheminee.dxs
```

Options utiles :

| Option | Effet |
|--------|-------|
| `--brightness 60` | Feu moins lumineux (60 %) |
| `--minutes 10` | Boucle de 10 minutes au lieu de 5 |
| `--fixture-rgb 20` | Pilote aussi un projecteur RGB sur la XLR, canaux 20, 21, 22 |
| `--fixture-dimmer 19` | Pilote aussi le gradateur d'un projecteur (canal 19) |
| `--relay-dmx 0` | Pour un nœud réglé `relay_dmx=0` (rubans dès `start_address`) |
| `--resume-s 30` | La conduite reprend 30 s après la fin du DMX |

Les canaux des rubans sont comptés **depuis l'adresse du nœud** (`+1` à `+4` avec le
relais sur `start_address`) : un même fichier sert à tous les nœuds rubans, quelle que
soit leur adresse. Les canaux d'un projecteur sont **absolus** (1 à 512).

Voir le résultat avant de le déployer :

```
PYTHONPATH=pi python3 -m dmxnow.cli show inspect shows/feu-de-cheminee.dxs
PYTHONPATH=pi enclosure/.venv/bin/python shows/preview.py shows/feu-de-cheminee.dxs -o feu.png
```

![Feu de cheminée : couleur du ruban et valeurs R, V, B, W sur 20 s](figures/feu-de-cheminee.png)

Une autre conduite (respiration, lever de soleil, orage, etc.) s'écrit de la même façon :
un script qui crée un `Show`, ajoute des images clés (`step(durée_ms, valeurs)`) et
écrit `encode()` dans un fichier. Le nœud fait un fondu linéaire d'une image à la
suivante, puis revient à la première. Claude Code peut écrire ces scripts à la demande.

## 3. Déployer

Depuis le Pi, démon lancé, nœud enrôlé et entendu (`dmxnow nodes`) :

```
dmxnow show deploy shows/feu-de-cheminee.dxs node-2442B0
dmxnow show deploy shows/feu-de-cheminee.dxs all        # tous les nœuds enrôlés entendus
```

Le fichier part en morceaux de 192 octets, nœud par nœud, puis le nœud vérifie sa taille
et son CRC avant de le jouer. Un fichier abîmé est refusé avant tout envoi. Si QLC+
envoie déjà l'univers du nœud, la conduite attend que le DMX s'arrête.

| Commande | Effet |
|----------|-------|
| `dmxnow show info node-2442B0` | Nom de la conduite, en cours ou en attente, durée de la boucle |
| `dmxnow show clear node-2442B0` | Efface la conduite (le nœud revient au comportement sans conduite) |
| `dmxnow nodes` | La marque `SHOW` signale les nœuds dont la conduite tourne |

Un `factory-reset` (ou un appui de 10 s sur SW1) efface aussi la conduite.

## 4. Points à vérifier au banc

Écrits et testés sur poste, pas encore essayés sur une vraie carte
([SPEC V-FW-09](../spec/SPEC.md)) :

- [ ] la conduite démarre seule à la mise sous tension, après le fondu d'allumage ;
- [ ] QLC+ reprend la main à sa première trame, la conduite revient 5 s après son arrêt ;
- [ ] le déploiement de 18 ko passe sans erreur (environ 94 morceaux) ;
- [ ] rendu du feu sur le ruban réel (couleur, vitesse du scintillement) ;
- [ ] `dmxnow show clear` puis redémarrage : plus de conduite.
