# Flash du firmware

Deux cartes à programmer : le **nœud** (ESP32-C3-MINI-1) et le **dongle** (Seeed XIAO
ESP32-C3). Les deux se programment par leur USB natif (USB Serial/JTAG de l'ESP32-C3),
sans adaptateur série.

## 1. Outils

Sur un PC (Linux, macOS ou Windows) :

```
pip install platformio            # ou esptool seul pour flasher un binaire fourni
git clone … && cd dmxnow/firmware
```

La plateforme est épinglée (pioarduino 55.03.312 : Arduino-ESP32 3.3.12 / ESP-IDF 5.5.5) :
le premier `pio run` la télécharge. Détails, tests, recette sur banc :
[firmware/README.md](../firmware/README.md).

Images produites :

| Fichier | Contenu | Usage |
|---------|---------|-------|
| `node/.pio/build/node/firmware.factory.bin` | chargeur + partitions + application | premier flash, à l'adresse **0x0** |
| `node/.pio/build/node/firmware.bin` | application seule | mise à jour **OTA** (page de maintenance) |
| `dongle/.pio/build/dongle/firmware.factory.bin` | image complète du dongle | premier flash à 0x0 |

## 2. Nœud, premier flash par J3

🔴 **Carte hors secteur.** Rien ne doit être branché sur J1, J4, J7 pendant la
programmation (ES-07). La carte est alimentée par l'USB, **par J3-5V uniquement**.

Pastilles **J3** (pas 2,54 mm, non équipées) :

| J3 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|----|---|---|---|---|---|---|---|
| Signal | 3V3 ⛔ | **GND** | **D−** | **D+** | EN | BOOT | **5V** |
| Câble USB | - | noir | blanc | vert | - | - | rouge |

- Câble USB-A (ou USB-C) coupé, ou connecteur USB de récupération : **5V → pastille 7**,
  GND → 2, D− → 3, D+ → 4. Les couleurs ci-dessus sont les plus courantes, **à vérifier au
  multimètre** sur le câble utilisé.
- ⛔ **Jamais la pastille 1 (3V3)** : c'est la sortie du régulateur, l'alimenter en
  retour n'est pas garanti ([REVIEW.md 7.6](../hardware/REVIEW.md)).
- Un connecteur 1×7 au pas de 2,54 mm tenu à la main (ou des pointes à ressort) suffit ;
  ne pas souder de connecteur à demeure (le trou doit rester libre pour le boîtier).

Procédure :

1. Maintenir **SW1** enfoncé, brancher l'USB, relâcher SW1 : l'ESP32-C3 démarre sur son
   chargeur ROM (mode téléchargement). Le port apparaît (`/dev/ttyACM0`, `COMx`).
2. Flasher :
   ```
   cd firmware/node
   pio run -e node -t upload
   ```
   ou, avec un binaire fourni :
   ```
   esptool.py --chip esp32c3 --port /dev/ttyACM0 write_flash 0x0 firmware.factory.bin
   ```
3. Débrancher et rebrancher l'USB (sans SW1). Ouvrir la console :
   ```
   pio device monitor -b 115200
   ```
   On lit la version, la variante (`strips` = carte entière, `fixture only` = carte
   cassée), le nom `node-XXXXXX` (fin de l'adresse MAC) et le **mot de passe de
   maintenance** aléatoire. **Noter le nom** : il sert à l'enrôlement.
4. Débrancher. Le nœud peut être monté et câblé ([assemblage.md](assemblage.md),
   [cablage.md](cablage.md)).

Si le port n'apparaît pas : vérifier D+/D− (inversés = pas d'énumération), l'alimentation
5V, et refaire l'étape 1 en maintenant bien SW1 pendant le branchement.

## 3. Dongle

1. Brancher le XIAO en USB-C sur le PC. La première fois, s'il n'est pas reconnu en
   mode téléchargement : **maintenir BOOT en branchant** (boîtier encore ouvert).
2. Flasher :
   ```
   cd firmware/dongle
   pio run -e dongle -t upload
   ```
3. Les mises à jour suivantes se font de la même manière, boîtier fermé : l'USB
   Serial/JTAG passe seul en mode téléchargement. Arrêter le démon avant sur le Pi
   (`sudo systemctl stop dmxnowd`), sinon le port est occupé ; le relancer ensuite.

## 4. Mises à jour du nœud par OTA

Une fois le nœud installé, il ne se reprogramme plus par J3 (il est sous secteur) : on
passe par la page de maintenance, **boîtier fermé**.

1. Construire `firmware.bin` (`pio run -e node`) et le copier sur un téléphone ou un
   portable.
2. Passer le nœud en maintenance ([mise-en-service.md §5](mise-en-service.md)), se
   connecter au point d'accès `dmxnow-<nom>`, ouvrir http://192.168.4.1/.
3. « Firmware » → choisir `firmware.bin` → « Téléverser ». Le nœud redémarre sur la
   nouvelle image.
4. La nouvelle image n'est **confirmée qu'au premier paquet radio valide** reçu du dongle.
   Sans paquet dans les 60 s, le nœud marque l'image invalide et redémarre sur
   l'ancienne. Faire les OTA **à portée du dongle, démon en marche**.
5. Vérifier la version avec `dmxnow nodes` (colonne `fw`).

Téléverser `firmware.bin`, jamais `firmware.factory.bin`, par la page web.
