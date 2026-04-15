# Installazione Rapida

## 1. Installa sidplayfp

### macOS
```bash
brew install sidplay
```

### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install sidplay
```

### Linux (Fedora)
```bash
sudo dnf install sidplay
```

### Windows
1. Scarica da: https://www.hvsc.c64.org/demo_systems.htm
2. Estrai e aggiungi `sidplayfp.exe` al PATH

---

## 2. Installa Python dependencies

```bash
cd sidplay
pip install -r requirements.txt
```

---

## 3. (Opzionale) Configura

```bash
# Crea il file di configurazione
cp sidplayer.cfg.example sidplayer.cfg

# Modifica con il tuo editor
nano sidplayer.cfg
# oppure
open -e sidplayer.cfg  # macOS
```

### Configura API (opzionale)

**RAWG.io:**
1. Vai su https://rawg.io/apidocs
2. Registrati e ottieni API key
3. Inserisci in `sidplayer.cfg`:
   ```ini
   [api]
   rawg_api_key = tua_key_qui
   ```

**IGDB:**
1. Vai su https://api-docs.igdb.com/#authentication
2. Crea app e ottieni credenziali
3. Inserisci in `sidplayer.cfg`:
   ```ini
   [api]
   igdb_client_id = tuo_client_id
   igdb_access_token = tuo_token
   ```

---

## 4. (Opzionale) Configura STIL

Per avere i titoli dei subsong:

1. Scarica HVSC da: https://www.hvsc.c64.org/
2. Estrai `STIL.txt`
3. Posizionalo in una di queste cartelle:
   - `~/Music/HVSC/STIL.txt`
   - `~/HVSC/STIL.txt`
   - Nella stessa cartella di `sid_play6.py`

Oppure configura in `sidplayer.cfg`:
```ini
[paths]
stil_path = /percorso/del/tuo/STIL.txt
```

---

## 5. Avvia!

```bash
python sid_play6.py
```

### Primo avvio
1. Clicca **LOAD**
2. Scegli "SID FILES" o "PLAYLIST"
3. Clicca **PLAY**

---

## Comandi Utili

| Comando | Descrizione |
|---------|-------------|
| `python sid_play6.py` | Avvio normale |
| `python sid_play6.py -d` | Con debug |
| `python sid_play6.py -h` | Mostra aiuto |
| `tail -f sidplayer_debug.log` | Vedi log in tempo reale |

---

## Risoluzione Problemi

### "sidplayfp: command not found"
```bash
# Verifica installazione
which sidplayfp

# Se non trovato, reinstalla
brew install sidplay  # macOS
sudo apt install sidplay  # Linux
```

### "ModuleNotFoundError: No module named 'PIL'"
```bash
pip install Pillow
```

### "ModuleNotFoundError: No module named 'requests'"
```bash
pip install requests
```

### Le copertine non vengono scaricate
1. Controlla di avere API keys in `sidplayer.cfg`
2. Verifica connessione internet
3. Guarda il log: `cat sidplayer_debug.log`

### STIL non viene caricato
1. Controlla che `STIL.txt` esista
2. Verifica il percorso in `sidplayer.cfg`
3. Guarda il log per errori

---

## Prossimi Passi

1. **Crea una playlist** - Copia `playlist.txt.example` e aggiung i tuoi file SID
2. **Scarica copertine** - Configura IGDB/RAWG per avere le copertine automatiche
3. **Organizza la libreria** - Crea una cartella per i tuoi file SID

---

## Supporto

- **Documentazione completa**: `README.md`
- **Debug e troubleshooting**: `README_DEBUG.md`
- **Esempio configurazione**: `sidplayer.cfg.example`
- **Esempio playlist**: `playlist.txt.example`
