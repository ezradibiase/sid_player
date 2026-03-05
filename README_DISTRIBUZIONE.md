# SIDPlayer C64 - Istruzioni per la Distribuzione

## Panoramica

SIDPlayer è un lettore di musica SID per file Commodore 64 con interfaccia grafica retrò e supporto per copertine dei giochi.

## Requisiti di Sistema

- **macOS**: 10.13 o superiore (consigliato macOS 13+)
- **Python**: 3.12+ (per eseguire lo script)
- **sidplayfp**: Installato nel sistema (`brew install sidplayfp`)

## Struttura dell'Applicazione

```
sid_player/
├── sid_play5.py              # Script principale
├── sidplayer.cfg             # File di configurazione
├── sidplayer.cfg.example     # Esempio di configurazione
├── C64Pro-Regular.ttf        # Font C64 (incluso nell'app)
├── commodore.icns            # Icona dell'app
├── SIDPlayer.app/            # App Bundle macOS
│   └── Contents/
│       ├── MacOS/
│       │   ├── launch.sh     # Script di avvio
│       │   ├── sid_play5.py  # Script principale
│       │   ├── C64Pro-Regular.ttf  # Font
│       │   └── sidplayer.cfg       # Configurazione
│       └── Resources/
│           └── commodore.icns      # Icona
├── images/                   # Immagini dei giochi (locale)
└── playlist.txt              # Playlist predefinita
```

## Configurazione

Il file `sidplayer.cfg` contiene tutte le impostazioni:

```ini
[paths]
# Directory dove salvare le immagini dei giochi
images_dir = ~/Pictures/SIDPlayer

# File della playlist
playlist_file = playlist.txt

# File del font C64
font_file = C64Pro-Regular.ttf

[api]
# API Key per RAWG.io (opzionale)
rawg_api_key = 

# IGDB Client ID e Access Token (opzionale, per copertine)
igdb_client_id = 
igdb_access_token = 

[player]
sidplay_cmd = sidplayfp
font_family = C64 Pro Mono

[window]
width = 640
height = 480
resizable = false
```

### Directory Immagini

Le immagini dei giochi vengono salvate in `~/Pictures/SIDPlayer` per default. Questa directory:
- **Non** è inclusa nell'app bundle
- È condivisa tra tutte le installazioni
- Viene creata automaticamente al primo avvio

### API per le Copertine

Per scaricare automaticamente le copertine dei giochi C64:

1. **IGDB** (consigliato per copertine):
   - Vai su https://dev.twitch.tv/console/apps
   - Crea una nuova applicazione
   - Copia Client ID e genera un Access Token
   - Inseriscili in `sidplayer.cfg`

2. **RAWG.io** (alternativa):
   - Vai su https://rawg.io/apidocs
   - Richiedi una API key gratuita
   - Inseriscila in `sidplayer.cfg`

## Distribuzione ad Altri Utenti

### Opzione 1: App Bundle (Consigliato)

L'App Bundle `SIDPlayer.app` è **portabile** e include:
- ✅ Script Python
- ✅ Font C64
- ✅ Configurazione predefinita
- ✅ Icona Commodore

**Cosa NON è incluso:**
- ❌ Python (l'utente deve averlo installato)
- ❌ Librerie Python (Pillow, requests, pyobjc)
- ❌ sidplayfp (deve essere installato separatamente)

**Istruzioni per l'utente finale:**

```bash
# 1. Installa Python 3.12+ da https://python.org
# 2. Installa le librerie necessarie
pip3 install pillow requests pyobjc

# 3. Installa sidplayfp
brew install sidplayfp

# 4. Copia SIDPlayer.app in Applicazioni
cp -r SIDPlayer.app /Applications/

# 5. Avvia l'app
open /Applications/SIDPlayer.app
```

### Opzione 2: PyInstaller (Eseguibile Standalone)

Per creare un eseguibile che include **tutto** (Python + librerie):

```bash
# Installa PyInstaller
pip3 install pyinstaller

# Crea l'eseguibile standalone
pyinstaller --onefile --windowed --icon=commodore.icns \
  --name="SIDPlayer" --add-data "C64Pro-Regular.ttf:." \
  --add-data "sidplayer.cfg:." sid_play5.py
```

L'eseguibile sarà in `dist/SIDPlayer` (~80-100MB).

**Vantaggi:**
- ✅ Nessuna dipendenza da installare
- ✅ Funziona su qualsiasi Mac
- ✅ Include tutto il necessario

**Svantaggi:**
- ❌ File grande (~100MB)
- ❌ Più lento all'avvio

## Risoluzione Problemi

### Il font non viene caricato

Verifica che `C64Pro-Regular.ttf` sia nella stessa directory dello script o aggiorna `font_file` in `sidplayer.cfg` con il percorso assoluto.

### Le immagini non vengono scaricate

1. Controlla che `requests` sia installato: `pip3 install requests`
2. Verifica le API key in `sidplayer.cfg`
3. Controlla i log in `SIDPlayer.app/Contents/MacOS/sidplayer.log`

### L'icona nel dock non è quella Commodore

Assicurati che:
1. `commodore.icns` sia in `SIDPlayer.app/Contents/Resources/`
2. Stai avviando l'app bundle, non lo script Python direttamente

### sidplayfp non trovato

Installa il player SID:
```bash
brew install sidplayfp
```

Oppure modifica `sidplay_cmd` in `sidplayer.cfg` con il percorso completo:
```ini
[player]
sidplay_cmd = /usr/local/bin/sidplayfp
```

## Aggiornamenti

Per aggiornare l'applicazione:

1. Scarica la nuova versione di `sid_play5.py`
2. Sostituisci il file in `SIDPlayer.app/Contents/MacOS/`
3. Riavvia l'app

La configurazione e le immagini esistenti vengono mantenute.

## Licenze

- **Font C64 Pro Mono**: Licenza open-source (GitHub: mborgbrant/c64-pro-mono)
- **SIDPlayer**: Codice personale per uso privato
