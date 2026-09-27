# dmxnow

Nœuds DMX et rubans LED sans fil sur ESP-NOW, pilotés depuis QLC+ sur Raspberry Pi.

Un boîtier monté sur le cordon secteur de chaque projecteur reçoit l'univers DMX
par radio (ESP-NOW), le restitue en DMX filaire, commute l'alimentation du
projecteur par relais et, dans sa version complète, pilote 4 canaux PWM de rubans LED.

> **Statut : spécification en cours de validation.** Aucune implémentation n'est
> écrite tant que `spec/` n'est pas validé.

| Dossier      | Contenu                                                         |
|--------------|-----------------------------------------------------------------|
| `spec/`      | [SPEC.md](spec/SPEC.md), [PROTOCOL.md](spec/PROTOCOL.md), [ADR](spec/adr/) |
| `hardware/`  | Projet KiCad, scripts de génération, sorties JLCPCB (à venir)   |
| `firmware/`  | `common/` (protocole, testé nativement), `node/` ; `dongle/` à venir |
| `pi/`        | Démon `dmxnowd`, CLI `dmxnow`, systemd, udev, `install.sh`      |
| `enclosure/` | Boîtier CadQuery paramétrique, deux variantes, STL/STEP         |
| `docs/`      | Assemblage, câblage, flash, mise en service, sécurité (à venir) |

⚠️ Ce projet manipule du 230 V. Toute la partie secteur est soumise à relecture
humaine obligatoire par une personne qualifiée avant fabrication et mise sous tension.
