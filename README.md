# SIDPlayer C64

Player di file **SID** (Commodore 64) con interfaccia grafica ispirata al Commodore Datasette, supporto copertine dei giochi e playlist personalizzate.

![Version](https://img.shields.io/badge/version-v6.1-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)
![Python](https://img.shields.io/badge/python-3.10+-blue)

---

## Caratteristiche

- Interfaccia grafica ispirata al **Commodore Datasette VC-1530**
- **Finestrella** con cover del gioco, titolo, autore, anno e numero traccia
- Riproduzione file `.sid` tramite `sidplayfp`
- Controllo volume in tempo reale con pulsante mute
- Pausa e ripresa della riproduzione
- Navigazione playlist: brano precedente (◄◄) e successivo (▶▶)
- Selezione del device di output audio (incluse casse Bluetooth)
- Playlist personalizzate con supporto subsong
- Copertine dei giochi da IGDB e RAWG (opzionale, richiede API key)
- Supporto STIL per i titoli dei subsong
- Funziona su macOS, Linux e Windows

---

## Requisiti

### Dipendenze di sistema

**sidplayfp** — il motore di riproduzione SID:

```bash
# macOS
brew install sidplayfp

# Linux (Debian/Ubuntu)
sudo apt install sidplayfp

# Windows
# Scarica da: https://sourceforge.net/projects/sidplay-residfp/
```

### Dipendenze Python

```bash
pip install -r requirements.txt
```

Contenuto di `requirements.txt`:
```
Pillow>=10.0
requests>=2.28
sounddevice>=0.4
numpy>=1.24
```

Il font **C64 Pro Mono** è opzionale ma consigliato: senza di esso viene usato Courier come fallback.

---

## Installazione e avvio

```bash
git clone https://github.com/ezradibiase/sid_player.git
cd sid_player
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
python3 sidplayer.py
```

**macOS — doppio clic:**
Rendi eseguibile `start_sidplayer.command` e aprilo dal Finder.

**Windows:**
Doppio clic su `start_sidplayer.bat`.

---

## Configurazione

Il file di configurazione viene creato automaticamente nella posizione canonica per la piattaforma:

| Sistema | Percorso |
|---------|----------|
| macOS | `~/Library/Application Support/SIDPlayer/sidplayer.cfg` |
| Linux | `~/.config/SIDPlayer/sidplayer.cfg` |
| Windows | `%APPDATA%\SIDPlayer\sidplayer.cfg` |

Per personalizzarlo, copia il file di esempio nella posizione corretta:

```bash
# macOS
cp sidplayer.cfg.example ~/Library/Application\ Support/SIDPlayer/sidplayer.cfg
```

Struttura di `sidplayer.cfg`:

```ini
[paths]
# Directory dove salvare le copertine scaricate
images_dir = ~/Pictures/SIDPlayer

# File playlist caricato automaticamente all'avvio
playlist_file = playlist.txt

# Percorso STIL.txt (lascia vuoto per ricerca automatica)
stil_path =

[api]
# RAWG.io API Key (opzionale)
rawg_api_key =

# IGDB Credentials (opzionale, consigliato per le copertine)
igdb_client_id =
igdb_access_token =

[player]
# Comando sidplayfp (deve essere nel PATH)
sidplay_cmd = sidplayfp

[window]
width = 640
height = 580
resizable = false
```

### Ottenere le API key (opzionale)

Senza API key il player funziona normalmente, ma non scarica le copertine dei giochi.

**IGDB** (consigliato):
1. Vai su https://dev.twitch.tv/console/apps e crea un'applicazione
2. Copia **Client ID** e genera un **Access Token**
3. Inseriscili in `sidplayer.cfg`

**RAWG.io** (alternativa):
1. Vai su https://rawg.io/apidocs e richiedi una API key gratuita
2. Inseriscila in `sidplayer.cfg`

---

## Playlist

Crea un file di testo con un file SID per riga:

```
# I commenti iniziano con #
/percorso/assoluto/Commando.sid
/percorso/assoluto/LastNinja.sid:2
~/Music/SID/Hubbard_Rob/International_Karate.sid:1
```

Il numero dopo i due punti specifica il **subsong** (traccia). Se omesso, usa la traccia 1.

Per usare una playlist come default all'avvio, imposta `playlist_file` in `sidplayer.cfg`.

---

## Interfaccia

### Finestrella

Il pannello centrale, ispirato alla finestrella trasparente del Datasette, mostra:
- **Cover del gioco** (da IGDB o RAWG) a sinistra
- **Titolo**, subtitle STIL, **autore**, anno di rilascio e numero traccia a destra
- Il banner dell'applicazione viene mostrato prima che inizi la riproduzione

### Bottoni utility

| Pulsante | Funzione |
|----------|----------|
| **LOAD** | Carica file SID o una playlist |
| **OUT** | Seleziona il device di output audio |
| **ABOUT** | Informazioni sull'applicazione |
| **VOL** | Slider volume (0–100%) |
| **M** | Mute / unmute |

### Bottoni trasporto (stile Datasette)

| Pulsante | Funzione |
|----------|----------|
| **◄◄ PREV** | Torna al brano precedente (risuona il primo se già al primo) |
| **▶ PLAY / ⏸ PAUSE** | Avvia la riproduzione; durante il play alterna pausa e ripresa |
| **▶▶ NEXT** | Passa alla traccia successiva |
| **■ STOP** | Ferma la riproduzione |

Per chiudere l'applicazione usa la **✕** del window manager (la finestra salva lo stato correttamente).

### Selezione output audio

Il pulsante **OUT** apre un popup con tutti i device audio disponibili nel sistema, incluse le casse Bluetooth connesse. Permette di separare l'audio del player dall'audio di sistema.

Il device selezionato viene usato dalla traccia successiva in poi.

---

## Compilare l'app bundle (macOS)

Per creare un'app `.app` autonoma per macOS:

```bash
pip install pyinstaller
cd scripts
pyinstaller SIDPlayer.spec
```

L'app viene creata in `scripts/dist/SIDPlayer.app`.

---

## Risoluzione problemi

### Durata dei brani: come funziona

SIDPlayer usa il flag `-os` di `sidplayfp` (single track mode): ogni brano viene suonato **una volta sola** e poi `sidplayfp` termina automaticamente in base alla durata registrata nell'HVSC Songlengths database.

Per farlo funzionare correttamente, scarica la HVSC (vedi sezione STIL) e imposta il percorso del database in `~/.config/sidplayfp/sidplayfp.ini`:

```ini
[SIDPlayfp]
Songlength Database = /percorso/a/HVSC/DOCUMENTS/Songlengths.md5
```

### "sidplayfp not found"
Installa `sidplayfp` (vedi Requisiti) e verifica che sia nel PATH:
```bash
which sidplayfp
```
Se è in un percorso non standard, impostalo in `sidplayer.cfg`:
```ini
[player]
sidplay_cmd = /opt/homebrew/bin/sidplayfp
```

### Le copertine non vengono scaricate
- Verifica che le API key siano configurate in `sidplayer.cfg`
- Controlla la connessione internet
- I log si trovano in `sidplayer_debug.log`

### Il font non è quello C64
Installa il font **C64 Pro Mono** e riavvia l'app. Senza di esso viene usato Courier come fallback.

### Log di debug
```bash
tail -f sidplayer_debug.log
```
Per abilitare output verbose nel terminale:
```bash
python3 sidplayer.py -d
```

---

## STIL (SID Tune Information List)

STIL contiene titoli e note sui subsong dell'HVSC. Per usarlo:
1. Scarica la HVSC da https://www.hvsc.c64.org/
2. Imposta il percorso di `STIL.txt` in `sidplayer.cfg`, oppure mettilo in una delle posizioni cercate automaticamente:
   - `./STIL.txt`
   - `~/Music/HVSC/STIL.txt`
   - `~/HVSC/STIL.txt`

---

## Crediti

- **Autore**: ezrad & IA (2026)
- **HVSC**: High Voltage SID Collection per i file SID
- **sidplayfp**: motore di riproduzione SID
- **Font**: C64 Pro Mono

## Link utili

- [HVSC - High Voltage SID Collection](https://www.hvsc.c64.org/)
- [sidplayfp](https://github.com/libsidplayfp/sidplayfp)
- [IGDB API](https://api-docs.igdb.com/)
- [RAWG.io API](https://rawg.io/apidocs)
- [C64 Pro Mono Font](https://github.com/mborgbrant/c64-pro-mono)

## Licenza

MIT — vedi [LICENSE](LICENSE).

## Trademark

"Commodore" e il logo Commodore sono marchi dei rispettivi proprietari.
Questo progetto è un'opera fan indipendente e non è affiliato, approvato
o connesso a Commodore Business Machines Ltd o a qualsiasi entità correlata.
