# SIDPlayer - Debug e Esecuzione

## Modalità Debug

### Avviare con debug
```bash
python sid_play6.py -d
```

Oppure:
```bash
python sid_play6.py --debug
```

### Cosa fa il debug mode
- Mostra a video tutti i messaggi di diagnostica
- Utile per capire problemi con API, STIL, copertine, ecc.
- I messaggi vengono SEMPRE scritti su `sidplayer_debug.log` (anche senza `-d`)

### Aiuto in linea
```bash
python sid_play6.py -h
```

Output:
```
SIDPlayer C64 v4.0

Utilizzo: python sid_play6.py [opzioni]

Opzioni:
  -d, --debug    Abilita messaggi di debug a video
  -h, --help     Mostra questo aiuto

Esempi:
  python sid_play6.py          # Avvio normale (silenzioso)
  python sid_play6.py -d       # Avvio con debug
```

---

## Esecuzione in Background

### Su macOS / Linux

#### Metodo 1: `&` (semplice)
```bash
python sid_play6.py &
```

#### Metodo 2: `nohup` (rimane attivo dopo logout)
```bash
nohup python sid_play6.py > /dev/null 2>&1 &
```

#### Metodo 3: `disown` (dopo aver avviato)
```bash
python sid_play6.py &
disown
```

### Su Windows

#### Metodo 1: `start` (apre nuova finestra)
```cmd
start python sid_play6.py
```

#### Metodo 2: PowerShell background
```powershell
Start-Process python -ArgumentList "sid_play6.py" -WindowStyle Hidden
```

#### Metodo 3: VBScript (completamente silenzioso)
Crea un file `run_sidplayer.vbs`:
```vbscript
Set objShell = CreateObject("WScript.Shell")
objShell.Run "python sid_play6.py", 0, False
```

Esegui:
```cmd
wscript run_sidplayer.vbs
```

---

## Log File

Tutti i messaggi di debug vengono scritti su:
```
sidplayer_debug.log
```

Questo file è utile per:
- Diagnosticare problemi
- Vedere quali API vengono chiamate
- Controllare errori di STIL, IGDB, RAWG
- Tracciare la riproduzione delle tracce

### Visualizzare il log in tempo reale

**macOS / Linux:**
```bash
tail -f sidplayer_debug.log
```

**Windows (PowerShell):**
```powershell
Get-Content sidplayer_debug.log -Wait -Tail 50
```

---

## Esempi d'uso

### 1. Avvio normale (silenzioso)
```bash
python sid_play6.py
```

### 2. Avvio con debug per troubleshooting
```bash
python sid_play6.py -d
```

### 3. Avvio in background e guarda il log
```bash
python sid_play6.py &
tail -f sidplayer_debug.log
```

### 4. Avvio da script (completamente silenzioso)
```bash
nohup python sid_play6.py > /dev/null 2>&1 &
```

---

## Risoluzione problemi

### Il player non si avvia
1. Controlla il log: `cat sidplayer_debug.log`
2. Avvia con debug: `python sid_play6.py -d`
3. Verifica che `sidplayfp` sia installato

### Le copertine non vengono scaricate
1. Controlla il log per errori IGDB/RAWG
2. Verifica le credenziali API in `sidplayer.cfg`
3. Avvia con debug per vedere le richieste API

### STIL non viene caricato
1. Controlla che `STIL.txt` esista
2. Verifica il percorso in `sidplayer.cfg`
3. Guarda il log per errori di parsing

### L'audio non funziona
1. Verifica che `sidplayfp` sia nel PATH
2. Controlla il volume di sistema
3. Prova un file SID diverso
