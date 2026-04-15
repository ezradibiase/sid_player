# SIDPlayer C64

Player di file SID (Commodore 64) con interfaccia grafica stile C64, supporto per copertine dei giochi e metadata STIL.

![Version](https://img.shields.io/badge/version-v4.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux%20%7C%20Windows-lightgrey)

## Caratteristiche

- 🎵 **Riproduzione file SID** tramite `sidplayfp`
- 🎨 **Interfaccia grafica** stile Commodore 64
- 🖼️ **Copertine dei giochi** da IGDB e RAWG (opzionale)
- 📝 **Supporto STIL** per titoli dei subsong
- 📋 **Playlist** con supporto multi-subsong
- ⚙️ **Configurazione** tramite file `.cfg`

## Requisiti

- **Python 3.7+**
- **sidplayfp** (High Voltage SID Player)
- **Pillow** e **requests** (Python packages)

### Installazione sidplayfp

**macOS:**
```bash
brew install sidplay
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt install sidplay
```

**Linux (Fedora):**
```bash
sudo dnf install sidplay
```

**Windows:**
Scarica da: https://www.hvsc.c64.org/demo_systems.htm

## Installazione

1. **Clona o scarica** questa directory:
```bash
cd sidplay
```

2. **Installa le dipendenze Python:**
```bash
pip install -r requirements.txt
```

3. **(Opzionale) Configura:**
```bash
cp sidplayer.cfg.example sidplayer.cfg
# Modifica sidplayer.cfg con le tue preferenze
```

## Utilizzo

### Avvio base
```bash
python sid_play6.py
```

### Con debug (messaggi a video)
```bash
python sid_play6.py -d
```

### Aiuto
```bash
python sid_play6.py -h
```

## Configurazione

### File `sidplayer.cfg`

```ini
[paths]
images_dir = ~/Pictures/SIDPlayer
playlist_file = playlist.txt
stil_path = ~/Music/HVSC/STIL.txt

[api]
rawg_api_key = your_key_here
igdb_client_id = your_client_id
igdb_access_token = your_token

[player]
sidplay_cmd = sidplayfp

[window]
width = 640
height = 480
resizable = false
```

### API Keys (opzionali)

- **RAWG.io**: https://rawg.io/apidocs
- **IGDB**: https://api-docs.igdb.com/#authentication

Senza API keys, il player funziona comunque ma usa solo immagini locali.

### STIL.txt

Per i titoli dei subsong, scarica HVSC con STIL.txt:
- https://www.hvsc.c64.org/

Posizioni cercate automaticamente:
- `./STIL.txt`
- `~/Music/HVSC/STIL.txt`
- `~/HVSC/STIL.txt`

## Playlist

Formato `playlist.txt`:
```
# Commenti iniziano con #
/percorso/Commando.sid
/percorso/LastNinja.sid:2
~/Music/SID/file.sid:1
```

Il `:numero` dopo il file specifica il subsong.

## Struttura File

```
sidplay/
├── sid_play6.py           # Applicazione principale
├── stil_reader.py         # Lettore STIL.txt
├── requirements.txt       # Dipendenze Python
├── sidplayer.cfg.example  # Esempio configurazione
├── playlist.txt.example   # Esempio playlist
├── README.md              # Questa documentazione
├── README_DEBUG.md        # Guida debug e troubleshooting
├── commodore.png          # Icona
└── sidplayer_banner.png   # Banner About
```

## Esecuzione in Background

**macOS/Linux:**
```bash
python sid_play6.py &
```

**Windows:**
```cmd
start python sid_play6.py
```

Vedi `README_DEBUG.md` per opzioni avanzate.

## Log File

Tutti i messaggi di debug vengono scritti su `sidplayer_debug.log`.

Per visualizzare in tempo reale:
```bash
tail -f sidplayer_debug.log
```

## Risoluzione Problemi

### "sidplayfp not found"
Installa sidplayfp (vedi Requisiti sopra).

### Copertine non scaricate
- Verifica API keys in `sidplayer.cfg`
- Controlla connessione internet
- Vedi log per errori: `cat sidplayer_debug.log`

### STIL non caricato
- Assicurati che `STIL.txt` esista
- Controlla il percorso in `sidplayer.cfg`

## Versioni

- **v4.0** - Supporto STIL, tre righe display (titolo, subsong, autore)
- **v3.0** - Versione clean senza controllo volume
- **v2.2** - Metadata SID per ricerca immagini
- **v2.1** - Supporto IGDB e RAWG
- **v1.9** - Versione base

## Crediti

- **Autore**: ezrad & IA
- **Anno**: 2026
- **Icona**: Commodore C64 style
- **Font**: C64 Pro Mono (o fallback Courier)

## License

Questo progetto è per uso personale e didattico.

## Link Utili

- **HVSC**: https://www.hvsc.c64.org/
- **SIDPlay**: https://sourceforge.net/projects/sidplay/
- **RAWG API**: https://rawg.io/apidocs
- **IGDB API**: https://api-docs.igdb.com/
