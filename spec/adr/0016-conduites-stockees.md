# ADR 0016 : Conduites stockées dans le nœud

**Statut :** Accepté (demande de l'utilisateur, 2026-10-13)

## Contexte

L'utilisateur veut qu'un nœud joue seul un effet, par exemple un feu de cheminée sur un
ruban RGBW, en boucle dès sa mise sous tension, sans Pi ni QLC+. Choix faits avec lui le
2026-10-13 :

- les conduites sont **générées** sur un poste (par Claude Code ou un script), puis
  déployées sur les nœuds ;
- QLC+ reprend la main dès qu'il envoie du DMX, la conduite reprend après quelques
  secondes sans flux ;
- la conduite pilote les rubans **et** la ligne DMX (projecteur sur la XLR).

## Décision

- Format `.dxs` : images clés en boucle, fondu linéaire, au plus 32 canaux, CRC-32
  (PROTOCOL §10.1). Les canaux sont relatifs à `start_address` (rubans : un même fichier
  sert à plusieurs nœuds) ou absolus (projecteur à adresse fixe).
- Le nœud interpole seulement : tout le calcul (aléatoire, couleur, raccord de la
  boucle) se fait à la génération, dans `pi/dmxnow/show.py` et les scripts de `shows/`.
- Stockage dans la partition `spiffs` existante (128 ko), lue par projection de la flash.
- Déploiement par quatre opcodes (`SHOW_WRITE`, `SHOW_COMMIT`, `SHOW_CLEAR`,
  `SHOW_INFO`, PROTOCOL §10.2), envoyés nœud par nœud par `dmxnow show`.
- Le relais ne suit jamais la conduite.

## Conséquences

- Aucun changement de la configuration NVS (le délai de reprise est dans le fichier) :
  un nœud déjà enrôlé garde son nom, sa clé et son mot de passe après la mise à jour.
- Aucun changement de la table de partitions : la mise à jour passe par OTA.
- Le firmware reste simple et testable sur poste (rendu C++ comparé au rendu Python sur
  les vecteurs communs).
- Un effet très riche (milliers d'images clés) coûte de la flash, pas du calcul : un feu
  de 5 minutes fait 18 ko sur 128 ko.
- Une conduite qui tourne se voit dans le heartbeat (bit 5 de `status`) et dans
  `dmxnow nodes` (marque `SHOW`).

## Alternatives écartées

- **Effets programmés dans le firmware** (feu, respiration, etc. avec paramètres) :
  chaque nouvel effet demande une mise à jour du firmware.
- **Enregistrement du flux QLC+ par le nœud** : demande QLC+ pour créer la conduite, et
  la reprise de la boucle se voit.
- **Interpréteur de script dans le nœud** (Lua, bytecode maison) : plus de code embarqué
  à valider, pour un gain nul quand la conduite peut être calculée à l'avance.
- **Envoi en broadcast** à tous les nœuds : un morceau perdu passerait inaperçu.
