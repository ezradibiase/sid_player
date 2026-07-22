# Changelog — SIDPlayer C64

Tutte le modifiche rilevanti al progetto sono documentate in questo file.

---

## [v6.4] — 2026-07-22

### Aggiunto
- **Drag & drop** (issue #3): trascina file `.sid`, intere cartelle (esplorate
  ricorsivamente) o file playlist (`.txt`/`.cfg`/`.lst`/`.m3u`/`.pls`) direttamente sulla
  finestra — vengono caricati e la riproduzione parte subito. Richiede `tkinterdnd2`
  (opzionale: se assente, l'app funziona comunque via LOAD).

### Modifiche
- Screenshot del README aggiornati: immagine principale con Athena (Martin Galway),
  aggiunte le schermate di boot e ABOUT nella sezione Interfaccia.
- Hint nella boot screen aggiornato per menzionare anche il drag & drop.

---

## [v6.3] — 2026-07-21

### Aggiunto
- **Copertine precise via database GB64** (`GBC_vNN.mdb`, stile [DeepSID](https://deepsid.chordian.net/)):
  match esatto titolo SID → gioco invece di indovinare dal nome file, zero chiamate di
  rete se configurato. Nuovo modulo `gb64_reader.py`, nuova config `gb64_mdb_path`.
- **Foto del musicista** accanto al nome autore (collezione GB64 locale, opzionale,
  config `gb64_photos_path`); nessun placeholder se manca, lo spazio resta nascosto.
- **Boot screen persistente** in stile C64 BASIC: è la prima schermata mostrata e resta
  finché non si carica un SID/playlist o parte la riproduzione, con layout fedele al
  vero schermo di boot (titolo e RAM centrati, READY. e hint allineati a sinistra).
- **Crediti in stile demoscene** nella schermata ABOUT (compositori SID storici, chip SID,
  HVSC Crew).
- Screenshot dell'interfaccia nel README.
- **PLAY disabilitato** finché non è caricato almeno un SID o una playlist (stesso
  meccanismo già usato per PREV/NEXT/STOP).

### Modifiche
- **Matching copertine IGDB/RAWG più prudente in generale** (non per singolo gioco):
  fix falsi positivi come "International Karate" → "IK+", "Trap" → "Space Trap",
  "Test" dentro "Super-Test"; normalizzazione apostrofi; rimosso il fallback rischioso
  "sola prima parola".
- `playlist_file` ora vuoto/opt-in di default (era `"playlist.txt"`), coerente con
  `hvsc_root`/`gb64_*` — chi clona il repo parte senza playlist auto-caricata.
- Messaggio dopo STOP semplificato: resta solo "STOPPED" (rimosso "Ready to load new
  files", fuorviante dato che le tracce restano caricate e si può già premere PLAY).
- Riorganizzazione file nella root del repo in `assets/`/`launchers/`; restyle del README.

### Fix
- Foto autore e tape counter non restano più "appesi" quando la playlist finisce o si
  preme STOP.
- Risolta sovrapposizione tra il messaggio di stato (es. avviso "No files found") e
  l'hint della boot screen.
- Il messaggio di conferma caricamento file/playlist non resta più rosso se in
  precedenza era stato mostrato un avviso di errore sulla stessa label.

---

## [v6.2] — 2026-07-07

### Aggiunto
- **Subsong selector nell'interfaccia**: frecce ◄ / ► per passare al subsong precedente/successivo
  durante la riproduzione, senza perdere la posizione in playlist.
- **Supporto playlist in formato standard HVSC**: path HVSC-relativi (es. `/Autore/Titolo.sid`),
  incluso il formato "ranked" con prefisso di posizione; nuova opzione `hvsc_root` in
  `sidplayer.cfg`. Quando una riga non specifica il subsong, viene letto il default song
  dichiarato nell'header del file SID (offset `0x10`) invece di forzare sempre la subsong 1.
- **Shuffle opzionale**: nuovo bottone **SHUF** per attivare/disattivare l'ordine casuale
  della playlist a runtime; opzione `shuffle` in `sidplayer.cfg` (default `true`).
- **Integrazione macOS Now Playing**: Control Center, Touch Bar, tasti F-media (F7/F8/F9)
  e Siri tramite il framework `MediaPlayer` (PyObjC), senza dipendenze aggiuntive.
- **Integrazione MTMR Touch Bar**: nome del gioco sempre visibile via file condiviso
  (`/tmp/.sidplayer_np`), indipendentemente dal subsong in riproduzione.
- Ritratto autore nella schermata **ABOUT**.
- Decorazione **"AUTO STOP"** con freccia stilizzata sotto la cover art, e etichetta
  **COUNTER** sotto le cifre del contatore nel badge Commodore.

### Modifiche
- **Restyling estetico della finestrella**: cornice esterna (bezel) e incavo interno
  ricalibrati con colori campionati da una foto reale del Datasette VC-1530, per
  richiamare più fedelmente il bezel metallico e lo sportello della cassetta.
- Filtro IGDB per le copertine ora applicato **server-side** (`where platforms = (15)`),
  con gestione più robusta dei formati di risposta cover.
- README aggiornato con nota di supporto **beta** per Linux/Windows.

### Fix
- Risolto crash `SIGABRT` nell'integrazione Now Playing (`PyEval_RestoreThread` con
  `tstate` nullo) dovuto a callback `MPRemoteCommandCenter` su thread ObjC arbitrari.
- Pulizia del file temporaneo MTMR garantita anche in caso di uscita anomala.

---

## [v6.1] — 2026-05-14

### Aggiunto
- **Nuova interfaccia grafica ispirata al Commodore Datasette VC-1530.**
- **Finestrella**: pannello centrale con bordo beige plastico e interno scuro che mostra
  cover del gioco, titolo, STIL subtitle, autore, anno di rilascio e numero traccia.
- **Banner di avvio**: `sidplayer_banner.png` mostrato nella finestrella prima che inizi
  la riproduzione; sostituito automaticamente dalla cover del gioco durante il play.
- **Bottone PREV** (◄◄): torna al brano precedente; al primo brano risuona dall'inizio.
- **PLAY/PAUSE unificato**: un unico bottone toggle che avvia, mette in pausa e riprende
  (simboli ▶ PLAY / ⏸ PAUSE / ▶ RESUME).
- Nuovi campi nella finestrella: `label_released` (anno/publisher) e `label_track`
  (numero traccia corrente sul totale).

### Modifiche
- Rimosso il pulsante **QUIT**: la finestra si chiude con la ✕ del window manager.
  Aggiunto `WM_DELETE_WINDOW` binding per terminare correttamente `sidplayfp`.
- Font dei bottoni utility ridotto a 10pt (il testo non fuoriesce più dai bordi).
- Bottoni di trasporto con palette beige Datasette (`#BBA888`, `relief="raised"`).
- **Config univoca per piattaforma** — rimossi i fallback a `~/` e alla directory
  dello script; la directory viene creata automaticamente se non esiste:
  - macOS: `~/Library/Application Support/SIDPlayer/sidplayer.cfg`
  - Linux: `~/.config/SIDPlayer/sidplayer.cfg`
  - Windows: `%APPDATA%\SIDPlayer\sidplayer.cfg`
- Finestra ridimensionata a **640×580** px.
- `load_and_display_image`: dimensione massima cover adattata a 180×180 px per la finestrella.

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
