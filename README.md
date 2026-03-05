# SIDPlayer C64 🎵🕹️

Un lettore musicale retro per file **SID** (Commodore 64) con interfaccia grafica stile C64, supporto per copertine dei giochi e playlist personalizzate.

![Version](https://img.shields.io/badge/version-2.2-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![Python](https://img.shields.io/badge/python-3.12+-blue)

---

## 📋 Indice

- [Caratteristiche](#-caratteristiche)
- [Requisiti](#-requisiti)
- [Installazione](#-installazione)
- [Utilizzo](#-utilizzo)
- [Configurazione](#-configurazione)
- [Playlist](#-playlist)
- [Struttura App Bundle](#-struttura-app-bundle)
- [Risoluzione Problemi](#-risoluzione-problemi)
- [Crediti](#-crediti)

---

## ✨ Caratteristiche

- **Interfaccia retrò C64** con colori e font originali
- **Supporto copertine giochi** da IGDB e RAWG (basato sui metadata SID)
- **Playlist personalizzate** con supporto subsong/traccia
- **Icona Commodore** personalizzata nel dock
- **Configurazione esterna** modificabile senza ricostruire l'app
- **Caricamento automatico** della playlist all'avvio
- **Randomizzazione** della playlist

---

## 🛠️ Requisiti

### Sistema Operativo
- **macOS** 10.13 o superiore (consigliato macOS 13+)

### Software
- **Python** 3.12+
- **sidplayfp** (player SID)

### Librerie Python
```bash
pip3 install pillow requests pyobjc
```

### Installa sidplayfp
```bash
brew install sidplayfp
```

---

## 📦 Installazione

### Opzione 1: App Bundle (Consigliato)

1. **Clona o scarica** il progetto:
```bash
cd ~/repos/personale/sid_player
```

2. **Crea l'app bundle**:
```bash
./build_app.sh
```

3. **Installa l'app**:
```bash
cp -r SIDPlayer.app /Applications/
```

4. **Avvia l'app**:
```bash
open /Applications/SIDPlayer.app
```

### Opzione 2: Esegui da script

```bash
python3 sid_play5.py
```

---

## 🎮 Utilizzo

### Pulsanti Principali

| Pulsante | Funzione |
|----------|----------|
| **LOAD** | Carica file SID o playlist |
| **PLAY** | Avvia la riproduzione |
| **NEXT** | Salta alla traccia successiva |
| **STOP** | Ferma la riproduzione |
| **ABOUT** | Informazioni sull'app |
| **QUIT** | Esci dall'applicazione |

### Caricare Musica

1. **Clicca LOAD**
2. **Scegli** cosa caricare:
   - **SID FILES**: Seleziona file `.sid` singoli
   - **PLAYLIST**: Seleziona un file playlist

3. **Clicca PLAY** per iniziare

### Playlist Automatica

All'avvio, l'app carica automaticamente la playlist configurata in `sidplayer.cfg`.

---

## ⚙️ Configurazione

### File di Configurazione

Il file `sidplayer.cfg` si trova in:
```
~/Library/Application Support/SIDPlayer/sidplayer.cfg
```

### Struttura del File

```ini
[paths]
# Directory dove salvare le immagini dei giochi
images_dir = ~/Pictures/SIDPlayer

# File della playlist predefinita
playlist_file = playlist.txt

[api]
# API Key per RAWG.io (opzionale)
rawg_api_key = 

# IGDB Client ID e Access Token (opzionale)
igdb_client_id = 
igdb_access_token = 

[player]
# Comando per riprodurre i file SID
sidplay_cmd = /opt/local/bin/sidplayfp

[window]
# Dimensioni della finestra
width = 640
height = 480
resizable = false
```

### Ottenere le API Key

#### IGDB (Consigliato per copertine)
1. Vai su https://dev.twitch.tv/console/apps
2. Crea una nuova applicazione
3. Copia **Client ID**
4. Genera un **Access Token**
5. Inseriscili in `sidplayer.cfg`

#### RAWG.io (Alternativa)
1. Vai su https://rawg.io/apidocs
2. Richiedi una API key gratuita
3. Inseriscila in `sidplayer.cfg`

---

## 📝 Playlist

### Formato

Le playlist supportano **qualsiasi estensione** (`.txt`, `.cfg`, `.lst`, `.m3u`, `.pls`, ecc.)

**Sintassi:**
```
# I commenti iniziano con #
/percorso/assoluto/file.sid:traccia
```

### Esempio

```ini
# La mia playlist C64 preferita
/Users/ezrad/Music/C64/Commando.sid:1
/Users/ezrad/Music/C64/Sanxion.sid:1
/Users/ezrad/Music/C64/Arkanoid.sid:2
/Users/ezrad/Music/C64/R-Type.sid:1
```

### Subsong/Traccia

Molti file SID contengono più musiche (subsongs). Il numero dopo i due punti (`:`) specifica quale traccia riprodurre:

- `file.sid:1` → Prima traccia (default)
- `file.sid:2` → Seconda traccia
- `file.sid:3` → Terza traccia

**Se non specificato**, viene usata la traccia **1** di default.

### Creare una Playlist

1. Crea un file di testo (es. `mia_playlist.txt`)
2. Aggiungi i percorsi ai file SID, uno per riga
3. Opzionalmente aggiungi `:numero` per specificare la traccia
4. Salva nella cartella che preferisci

### Caricare una Playlist

1. Clicca **LOAD**
2. Scegli **PLAYLIST**
3. Seleziona il file playlist
4. Clicca **PLAY**

---

## 🏗️ Struttura App Bundle

```
SIDPlayer.app/
└── Contents/
    ├── MacOS/
    │   ├── launch.sh          # Script di avvio
    │   ├── sid_play5.py       # Script principale
    │   ├── playlist.txt       # Playlist (inclusa)
    │   └── sidplayer_banner.png  # Banner About
    └── Resources/
        └── commodore.icns     # Icona dell'app
```

### Directory Esterne (Utente)

```
~/Library/Application Support/SIDPlayer/
├── sidplayer.cfg            # Configurazione
└── sidplayer_banner.png     # Banner (opzionale)

~/Pictures/SIDPlayer/
└── [immagini dei giochi]    # Copertine scaricate
```

---

## 🔧 Risoluzione Problemi

### L'app non si avvia

1. **Controlla i log**:
```bash
cat ~/Library/Application\ Support/SIDPlayer/sidplayer.log
```

2. **Verifica le dipendenze**:
```bash
python3 -c "import PIL; import requests; print('OK')"
which sidplayfp
```

### sidplayfp non trovato

**Sintomo**: Errore "sidplayfp not found in PATH"

**Soluzione**:
1. Installa sidplayfp:
```bash
brew install sidplayfp
```

2. Trova il percorso:
```bash
which sidplayfp
```

3. Aggiorna `sidplayer.cfg`:
```ini
[player]
sidplay_cmd = /opt/homebrew/bin/sidplayfp  # Apple Silicon
# oppure
sidplay_cmd = /usr/local/bin/sidplayfp     # Intel
```

### Le copertine non vengono scaricate

**Controlla**:
1. Le API key sono configurate in `sidplayer.cfg`
2. La connessione internet funziona
3. La directory `~/Pictures/SIDPlayer/` esiste ed è scrivibile

**Log**:
```bash
tail -50 ~/Library/Application\ Support/SIDPlayer/sidplayer.log
```

### Il font non è quello C64

Il font **C64 Pro Mono** deve essere installato nel sistema:

1. **Installa il font** (se non presente)
2. **Riavvia** l'app

Se non installato, viene usato **Courier** come fallback.

### La playlist non si carica

**Verifica**:
1. Il percorso nel file playlist è corretto
2. I file SID esistono
3. Il formato è corretto (`percorso:traccia`)

**Test**:
```bash
# Prova a caricare manualmente
python3 -c "
with open('playlist.txt') as f:
    for line in f:
        if line.strip() and not line.startswith('#'):
            print(line.strip())
"
```

---

## 📚 Crediti

### Autore
- **ezrad & IA** (2026)

### Ringraziamenti
- **HVSC** (High Voltage SID Collection) per i file SID
- **IGDB** per le copertine dei giochi
- **RAWG.io** per i metadata dei giochi
- **sidplayfp** developers

### Licenze
- **Font**: C64 Pro Mono (open-source)
- **Banner ASCII**: ezrad
- **Codice**: Uso personale

---

## 🔗 Link Utili

- [HVSC - High Voltage SID Collection](https://www.hvsc.c64.org/)
- [sidplayfp su GitHub](https://github.com/Legends2/sidplay-residfp)
- [IGDB API](https://api-docs.igdb.com/)
- [RAWG.io API](https://rawg.io/apidocs)
- [C64 Pro Mono Font](https://github.com/mborgbrant/c64-pro-mono)

---

## 📞 Supporto

Per problemi o suggerimenti:
- **GitHub**: [github.com/ezradibiase](https://github.com/ezradibiase)
- **Email**: ezradibiase@gmail.com

---

**Enjoy your C64 music!** 🎵🕹️
