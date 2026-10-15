# Rôle d'une carte : nœud ou dongle

Toutes les cartes nœud ont **le même firmware** (`firmware/node`). Chacune est un nœud par
défaut, et chacune peut servir de dongle : branchée en USB au Pi, elle émet les univers
par la radio vers les autres nœuds. La XIAO, elle, est toujours un dongle (firmware
`firmware/dongle`, antenne 5 dBi).

Détails techniques : [SPEC §4.15](../spec/SPEC.md),
[ADR 0018](../spec/adr/0018-firmware-unique-roles.md).

🔴 **Une carte qui sert de dongle n'est jamais raccordée au secteur.** Elle est reliée à un
ordinateur par l'USB et alimentée par lui (J3-5V, jamais J3-3V3). Rien sur J1, J4, J7.
Règle 2 de [securite.md](securite.md), relecture humaine obligatoire.

## 1. Les trois façons de choisir le rôle

| Façon | Commande | Durée |
|-------|----------|-------|
| **Automatique** | Brancher la carte en USB au Pi, démon lancé. Elle devient dongle au premier message du démon, en moins de 2 s. | Jusqu'à l'extinction : rebranchée sur le secteur, c'est de nouveau un nœud. |
| **Rôle enregistré** | `dmxnow role node-2442B0 dongle`, envoyé par la radio à un nœud enrôlé. Il redémarre en dongle. | À chaque mise sous tension, jusqu'au retour au nœud. |
| **Retour au nœud** | `dmxnow role dongle node`, envoyé par l'USB à la carte qui sert de dongle. | La carte redémarre en nœud et ne rebascule plus avant d'avoir été éteinte. |

Un `factory-reset` (ou SW1 appuyé 10 s) remet aussi la carte en nœud.

## 2. Remplacer le dongle par une carte nœud

1. Débrancher la carte du secteur 🔴, puis la relier en USB au Pi par ses pastilles J3
   (même câble que pour le flash, [flash.md §2](flash.md)).
2. Sur le Pi, faire pointer le démon vers son port. Avec l'installeur, la règle udev vise
   le numéro de série du dongle : relancer `sudo ./install.sh --dongle-serial <MAC de la
   carte>`, ou mettre le port dans `/etc/dmxnow/dmxnowd.toml` (`[dongle] port`).
3. `sudo systemctl restart dmxnowd`, puis vérifier :

   ```
   dmxnow status
   ```

   ```
   "board": "node board",
   "role": "automatic (until power-off)"
   ```

4. Les nœuds la retrouvent seuls (même canal, même `net_id` : le démon lui envoie sa
   configuration radio à la connexion).

En dongle, la carte sort aussi sur sa XLR l'univers de sa configuration (`universe` du
nœud, `dmx_out_slots` canaux) : un projecteur peut s'y brancher directement. Son relais
reste ouvert et ses sorties rubans à 0.

Sa portée est plus faible que celle de la XIAO : elle n'a que l'antenne du module. La
placer en hauteur, dégagée.

## 3. Rendre la carte à son rôle de nœud

- **Rôle automatique** : il suffit de la débrancher du Pi et de la remonter sur le
  secteur.
- **Rôle enregistré** : `dmxnow role dongle node` pendant qu'elle est branchée au Pi, puis
  la débrancher. Ou `factory-reset` (elle perd alors aussi son enrôlement).

## 4. À savoir

- Un nœud branché en USB à un poste qui fait tourner `dmxnowd` devient son dongle. Pour
  un flash ou un essai par l'USB (DMX par l'USB, [firmware/README.md](../firmware/README.md)),
  arrêter le démon avant.
- `dmxnow role <nœud> dongle` est refusé (`auth_failed`) à un nœud sans clé réseau,
  comme la mise à jour par la radio.
- La XIAO refuse `dmxnow role dongle node` : elle est toujours un dongle.
