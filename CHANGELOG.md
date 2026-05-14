# Changelog — SIDPlayer C64

Tutte le modifiche rilevanti al progetto sono documentate in questo file.

---

## [v6.0.3] — 2026-05-14

### Modifiche
- Rimosso completamente `play_time`: il parametro `-t` non viene mai più passato a `sidplayfp`.
  I brani vengono sempre eseguiti con `-os<N>` (single track mode): la durata è determinata
  esclusivamente dall'HVSC Songlengths database configurato in `~/.config/sidplayfp/sidplayfp.ini`.
- Rimosso `play_time` da `Config`, `AudioEngine` e `sidplayer.cfg.example`.
- Configurato `Songlength Database` in `~/.config/sidplayfp/sidplayfp.ini` con il percorso
  corretto al file `Songlengths.md5` dell'HVSC.

---

## [v6.0.2] — 2026-05-13

### Fix
- Rimosso il default `play_time = 3:30`: il timeout fisso tagliava i brani lunghi e
  faceva loopare quelli brevi. `sidplayfp` usa già `-os` (single track mode) che termina
  il brano automaticamente tramite l'HVSC Songlengths database. `play_time` rimane
  disponibile come fallback opt-in per brani non presenti nel database.

---

## [v6.0.1] — 2026-05-13

### Fix
- Corretto `AttributeError: 'SidTkPlayer' object has no attribute 'audio_engine'` all'avvio:
  `play_time` veniva assegnato all'engine prima che questo fosse istanziato nel costruttore `__init__`.

---

## [v6.0] — 2026-04-28

### Aggiunto
- Parametro `play_time` in `sidplayer.cfg` (default `3:30`): i brani privi di voce nell'HVSC
  Songlengths database terminano al timeout configurato invece di loopare all'infinito.
- Fetch delle copertine spostato in thread background: l'audio parte immediatamente senza
  attendere le chiamate API a IGDB/RAWG (eliminato un ritardo fino a 15 s).

### Documentazione
- Aggiornato README con sezione dedicata al parametro `play_time` e troubleshooting durata brani.
- Aggiornato `sidplayer.cfg.example` con la nuova chiave e relativa documentazione.

---

## [v6.0] — 2026-03-05  *(release iniziale pubblica)*

### Aggiunto
- Interfaccia grafica stile Commodore 64 (palette C64 originale, font C64 Pro Mono).
- Riproduzione file `.sid` tramite `sidplayfp` con supporto subsong.
- Controllo volume applicativo in tempo reale, indipendente dal volume di sistema
  (pipeline FIFO → sidplayfp → sounddevice / CoreAudio su macOS).
- Pulsante **OUT** per la selezione del device di output audio incluse casse Bluetooth.
- Pausa e ripresa della riproduzione (`SIGSTOP`/`SIGCONT` su macOS/Linux).
- Playlist personalizzate con supporto subsong (formato `percorso.sid:N`).
- Supporto STIL (SID Tune Information List) per i titoli dei subsong.
- Copertine dei giochi da **IGDB** e **RAWG.io** (opzionale, richiede API key).
- Modalità cross-platform: macOS, Linux, Windows (con gestione delle differenze FIFO/SIGSTOP).
- Bundle `.app` per macOS tramite PyInstaller (`scripts/SIDPlayer.spec`).
- Icona Commodore 64 personalizzata (`commodore.icns`).
- Banner grafico all'avvio (`sidplayer_banner.png`).
- File di configurazione `sidplayer.cfg` con sezioni `paths`, `api`, `player`, `window`.
- Log di debug su file (`sidplayer_debug.log`), modalità verbose con flag `-d`.

---

## [v1.x – v5.x] — 2026-03-04 *(sviluppo iniziale, non pubblico)*

Iterazioni prototipali (`sid_play.py` → `sid_play2.py` → ... → `sid_play5.py`):
- Prototipo base con riproduzione diretta via `sidplayfp`.
- Aggiunta interfaccia Tkinter con colori C64.
- Integrazione API IGDB per le copertine.
- Integrazione API RAWG.io come fallback.
- Selezione device audio via `sounddevice`.
- Script di build e bundle macOS (prima versione con `build_app.sh`).
