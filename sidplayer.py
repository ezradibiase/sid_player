#!/usr/bin/env python3
"""
SIDPlayer C64-Style con supporto copertine C64 da IGDB e RAWG e STIL
e controllo volume applicativo indipendente dal volume di sistema
Versione: v6.0.3 (Cross-platform, silent mode, terminal detach)
Autore: ezrad & IA
Anno: 2026
"""

import atexit
import os
import random
import re
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageTk
import configparser

# ---------------------------------------------------------------------------
# Piattaforma corrente
# ---------------------------------------------------------------------------
IS_WINDOWS        = sys.platform == 'win32'
IS_MACOS          = sys.platform == 'darwin'
IS_LINUX          = sys.platform.startswith('linux')
HAS_FIFO          = hasattr(os, 'mkfifo')          # False su Windows
HAS_PROCESS_PAUSE = hasattr(signal, 'SIGSTOP')     # False su Windows

# Import STIL Reader
from stil_reader import STILReader
from gb64_reader import GB64Database

# Integrazione macOS Now Playing (Control Center, Touch Bar, tasti media)
try:
    from nowplaying_mac import NowPlayingManager, HAS_NOWPLAYING
except ImportError:
    HAS_NOWPLAYING = False
    class NowPlayingManager:   # stub no-op su piattaforme senza il modulo
        def __init__(self, *a, **kw): pass
        def update(self, **kw):  pass
        def set_playing(self):   pass
        def set_paused(self):    pass
        def clear(self):         pass
        def deactivate(self):    pass

# ---------------------------------------------------------------------------
# MTMR Touch Bar helper — file condiviso /tmp/.sidplayer_np
# MTMR legge questo file ogni 2 secondi via shellScriptTitledButton.
# ---------------------------------------------------------------------------
_NP_FILE = "/tmp/.sidplayer_np"

def _np_write(artist: str, title: str) -> None:
    """Scrive il brano in riproduzione nel file condiviso con MTMR."""
    try:
        text = f"{artist} – {title}" if artist else title
        with open(_NP_FILE, "w", encoding="utf-8") as fh:
            fh.write(text)
    except Exception:
        pass

def _np_clear() -> None:
    """Rimuove il file condiviso (SIDPlayer fermo o uscito)."""
    try:
        os.unlink(_NP_FILE)
    except FileNotFoundError:
        pass
    except Exception:
        pass

# Garantisce la pulizia anche in caso di uscita anomala (crash, SIGTERM, Cmd+Q)
atexit.register(_np_clear)

# Configura logging su file
LOG_FILE = "sidplayer_debug.log"
DEBUG_MODE = False  # Viene impostato da main() se -d è presente

def log_message(msg):
    """Scrive un messaggio nel file di log (sempre attivo)"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, LOG_FILE)
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

def debug_print(msg):
    """Stampa a video solo se DEBUG_MODE è attivo"""
    if DEBUG_MODE:
        print(msg)

# Prova a importare requests per le API
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    log_message("ATTENZIONE: 'requests' non installato - supporto API disabilitato")

# Prova a importare sounddevice per il controllo volume
try:
    import sounddevice as sd
    import numpy as np
    HAS_SOUNDDEVICE = True
except ImportError:
    HAS_SOUNDDEVICE = False
    log_message("ATTENZIONE: 'sounddevice' non installato - uso riproduzione diretta")

VERSION = "v6.4"
FONT_FAMILY_DEFAULT = "C64 Pro Mono"
FONT_FALLBACK = "Courier"
CONFIG_FILE = "sidplayer.cfg"

C64_PALETTE = {
    "EZ_LBLUE": "#8B8FF7", "EZ_BLUE": "#383BF0", "EZ_DBLUE": "#3134D2",
    "BLACK": "#000000", "WHITE": "#FFFFFF", "RED": "#880000", "CYAN": "#AAFFEE",
    "PURPLE": "#CC44CC", "GREEN": "#00CC55", "BLUE": "#0000AA", "YELLOW": "#EEEE77",
    "ORANGE": "#DD8855", "BROWN": "#664400", "PINK": "#FF7777", "DARK_GREY": "#333333",
    "GREY": "#777777", "LIGHT_GREEN": "#AAFF66", "LIGHT_BLUE": "#0088FF", "LIGHT_GREY": "#BBBBBB"
}

DATASETTE = {
    "PLASTIC": "#ECE7D3",   # corpo esterno, RGB(236,231,211)
    "BODY":    "#BBA888",   # superficie bottone
    "HI":      "#DDCFB0",   # luce top-left
    "SH":      "#7A6848",   # ombra bottom-right
    "PRESSED": "#A09070",   # bottone premuto
    "DIS":     "#A89880",   # bottone disabilitato
    "DIS_TXT": "#706050",   # testo disabilitato
    "TEXT":    "#1A1208",   # testo/simbolo normale
    "BORDER":  "#5A4428",   # bordo esterno
    "GLASS":   "#0D0D0D",   # interno finestrella
    "BEZEL":   "#989BAC",   # cornice sottile, bezel metallico sportello cassetta
    "SLOT":    "#4B4B5D",   # cornice incavo vano cassetta, sui 4 lati
}

TRANSPORT = {
    "BG":        "#2D2019",   # sfondo badge "C= commodore" + barre, RGB(45,32,25)
    "BTN":       "#3B271E",   # tasto: rettangolo nero, senza testo dentro — RGB(59,39,30)
    "BTN_ACT":   "#4a4033",   # tasto premuto
    "BTN_DIS":   "#2a2520",   # tasto disabilitato
    "LEGEND_BG": "#BBBBBB",   # striscia grigia dietro etichette parola+simbolo
}


def get_available_font(preferred_font, fallback_font):
    """Verifica se il font preferito è disponibile nel sistema."""
    try:
        test_font = (preferred_font, 12)
        return preferred_font
    except:
        return fallback_font


class Config:
    """Gestisce la configurazione dell'applicazione"""

    DEFAULTS = {
        'paths': {
            'images_dir': '~/Pictures/SIDPlayer',
            'playlist_file': '',  # Playlist caricata all'avvio (opzionale, vuota di default)
            'stil_path': '~/Music/C64Music/STIL.txt',  # Percorso opzionale per STIL.txt
            'hvsc_root': '',  # Root locale della collezione HVSC, per playlist con path HVSC-relativi
            'gb64_boxart_path': '',  # Cartella locale "Cover" di una collezione GB64 (opzionale)
            'gb64_mdb_path': '',  # Percorso al file GBC_vNN.mdb di GB64, per match preciso (richiede mdbtools)
            'gb64_photos_path': '',  # Cartella locale foto musicisti GB64 (opzionale)
        },
        'api': {
            'rawg_api_key': '',
            'igdb_client_id': '',
            'igdb_access_token': '',
        },
        'player': {
            'sidplay_cmd': 'sidplayfp',
            'shuffle': 'false',
        },
        'window': {
            'width': '640',
            'height': '580',
            'resizable': 'false',
        }
    }

    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser()

        if not os.path.isabs(self.config_file):
            # Posizione canonica per piattaforma — unica, nessun fallback
            if IS_MACOS:
                config_dir = os.path.expanduser("~/Library/Application Support/SIDPlayer")
            elif IS_WINDOWS:
                config_dir = os.path.join(
                    os.environ.get('APPDATA', os.path.expanduser('~')), 'SIDPlayer')
            else:  # Linux e altri Unix
                config_dir = os.path.expanduser("~/.config/SIDPlayer")
            os.makedirs(config_dir, exist_ok=True)
            self.config_file = os.path.join(config_dir, self.config_file)
            log_message(f"Config: {self.config_file}")

        self._load_config()
        self._font_family = get_available_font(FONT_FAMILY_DEFAULT, FONT_FALLBACK)
        if self._font_family == FONT_FALLBACK:
            log_message(f"Font '{FONT_FAMILY_DEFAULT}' non trovato. Uso '{FONT_FALLBACK}'")
        else:
            log_message(f"Font '{FONT_FAMILY_DEFAULT}' disponibile")

    def _load_config(self):
        """Carica la configurazione dal file o usa i default"""
        for section, options in self.DEFAULTS.items():
            self.config.setdefault(section, {})
            for key, value in options.items():
                if key not in self.config[section]:
                    self.config[section][key] = value

        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                debug_print(f"✓ Configurazione caricata da: {self.config_file}")
            except Exception as e:
                debug_print(f"⚠ Errore lettura config: {e}. Uso i default.")
        else:
            debug_print(f"ℹ File {self.config_file} non trovato. Uso i default.")

    def get(self, section, option, fallback=None):
        return self.config.get(section, option, fallback=fallback)

    def getboolean(self, section, option, fallback=False):
        return self.config.getboolean(section, option, fallback=fallback)

    def getint(self, section, option, fallback=0):
        return self.config.getint(section, option, fallback=fallback)

    @property
    def images_dir(self):
        path = self.get('paths', 'images_dir')
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def playlist_file(self):
        path = self.get('paths', 'playlist_file')
        if not path:
            return None
        if not os.path.isabs(path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(script_dir, path)
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def stil_path(self):
        path = self.get('paths', 'stil_path')
        if not path:
            return None
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def hvsc_root(self):
        path = self.get('paths', 'hvsc_root')
        if not path:
            return None
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def gb64_boxart_path(self):
        path = self.get('paths', 'gb64_boxart_path')
        if not path:
            return None
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def gb64_mdb_path(self):
        path = self.get('paths', 'gb64_mdb_path')
        if not path:
            return None
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def gb64_photos_path(self):
        path = self.get('paths', 'gb64_photos_path')
        if not path:
            return None
        return os.path.expanduser(os.path.expandvars(path))

    @property
    def rawg_api_key(self):
        return self.get('api', 'rawg_api_key')

    @property
    def igdb_client_id(self):
        return self.get('api', 'igdb_client_id')

    @property
    def igdb_access_token(self):
        return self.get('api', 'igdb_access_token')

    @property
    def sidplay_cmd(self):
        return self.get('player', 'sidplay_cmd')

    @property
    def shuffle(self):
        return self.getboolean('player', 'shuffle', True)

    @property
    def font_family(self):
        return self._font_family

    @property
    def window_width(self):
        return self.getint('window', 'width', 640)

    @property
    def window_height(self):
        return self.getint('window', 'height', 580)

    @property
    def window_resizable(self):
        return self.getboolean('window', 'resizable', False)

    def ensure_directories(self):
        images_dir = self.images_dir
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
            debug_print(f"✓ Creata directory immagini: {images_dir}")
        return images_dir


# ---------------------------------------------------------------------------
# Utility condivisa: varianti del nome per la ricerca immagini
# ---------------------------------------------------------------------------

# Punteggiatura preservata nei nomi file oltre ad alfanumerici/spazio/trattini:
# distingue titoli che altrimenti collasserebbero sullo stesso nome dopo la
# sanitizzazione (es. "IK+" vs "IK", "Ghosts 'n Goblins"), causando cache
# condivisa fra giochi diversi. Nessuno di questi è invalido come nome file
# su macOS/Linux/Windows.
_SAFE_FILENAME_EXTRA_CHARS = (' ', '-', '_', '+', '!', '&', "'")


def _sanitize_filename(name):
    """Rimuove solo i caratteri non validi per un nome file, preservando la
    punteggiatura che distingue titoli diversi tra loro."""
    return "".join(c for c in name if c.isalnum() or c in _SAFE_FILENAME_EXTRA_CHARS).strip()


def _generate_name_variants(clean_name):
    """
    Restituisce una lista di varianti del nome del gioco da provare in sequenza,
    dalla più specifica alla meno specifica.

    Gestisce pattern tipici dei file SID della HVSC:
      "Elite Loader"          → ["Elite Loader", "Elite"]
      "Outrun"                → ["Outrun"]
      "Beyond the Forbidden Forest" → ["Beyond the Forbidden Forest", "Beyond the Forbidden"]
      "Commando Title Music"  → ["Commando Title Music", "Commando"]
    """
    # Suffissi tipici dei file SID che NON fanno parte del nome del gioco,
    # ordinati dal più lungo al più corto per evitare match parziali.
    SID_SUFFIXES = [
        'loading screen music', 'loading screen', 'loading music', 'loading',
        'ingame music', 'in-game music', 'in game music',
        'ingame', 'in-game', 'in game',
        'title screen music', 'title screen tune', 'title screen',
        'title music', 'title tune', 'title song', 'title',
        'main theme tune', 'main theme music', 'main theme',
        'theme music', 'theme tune', 'theme song', 'theme',
        'intro music', 'intro tune', 'intro',
        'high score music', 'high score tune', 'high score',
        'game over music', 'game over tune', 'game over',
        'ending music', 'ending theme', 'ending',
        'level music', 'level tune',
        'credits music', 'credits tune', 'credits',
        'loader music', 'loader tune', 'loader',
        'menu music', 'menu tune', 'menu',
        'bonus music', 'bonus tune', 'bonus level',
        'chip tune', 'chiptune',
        'part one', 'part two', 'part three', 'part four',
        'part 1', 'part 2', 'part 3', 'part 4',
        'part i', 'part ii', 'part iii', 'part iv',
    ]

    variants = [clean_name]
    name_lower = clean_name.lower()

    for suffix in SID_SUFFIXES:
        if name_lower.endswith(suffix):
            stripped = clean_name[:-(len(suffix))].strip().rstrip('-').rstrip(',').strip()
            if stripped and stripped.lower() != name_lower:
                variants.append(stripped)
            break

    # Senza l'ultima parola (cattura sottotitoli descrittivi)
    words = clean_name.split()
    if len(words) > 2:
        shorter = ' '.join(words[:-1])
        if shorter not in variants:
            variants.append(shorter)

    # NB: niente fallback "solo la prima parola". Una singola parola generica
    # ("Test", "Ghouls", "MicroProse"...) tende a matchare esattamente un
    # gioco completamente diverso invece del titolo cercato — non esiste una
    # lista di parole "sicure" abbastanza completa da evitarlo in generale.
    # I titoli SID che sono già una sola parola (es. "Trap") restano intatti:
    # sono la prima variante provata, non passano da questo fallback.

    return variants


def _title_match_score(result_title, query):
    """
    Restituisce uno score 0-100 che misura quanto result_title corrisponde alla query.

    Penalizza:
      - Sequel/varianti con parole extra  ("Saboteur II" per query "Saboteur" → 30)
      - Prefissi aggiunti             ("Super R-Type" per query "R-Type"   → 20)
      - Giochi non correlati                                                → 5

    Accetta:
      - Match esatto                                                        → 100
      - Stesso titolo con/senza spazi ("Ghetto Blaster" ↔ "Ghettoblaster") → 88
      - Titolo + sottotitolo separato ("Saboteur: Dossier Argus")          → 90
    """
    import re

    # Rimuove apostrofi (dritti e curvi) prima di ogni confronto: la stessa
    # stringa può comparire come "Ghouls 'n Ghosts" su un database e
    # "Ghouls 'n' Ghosts" sull'header SID — senza normalizzare, il match
    # esatto/quasi-esatto fallisce e si scivola verso varianti più rischiose.
    def _strip_apostrophes(s):
        return re.sub(r"[''`]", '', s)

    r = _strip_apostrophes(result_title.lower().strip())
    q = _strip_apostrophes(query.lower().strip())
    if not q:
        return 0

    # Esatto
    if r == q:
        return 100

    # Stesso nome con/senza spazi (Ghettoblaster ↔ Ghetto Blaster)
    if r.replace(' ', '') == q.replace(' ', ''):
        return 88

    # Titolo + sottotitolo (usa " - " o ": " con spazi → non rompe "R-Type")
    def core(s):
        # Rimuove sottotitolo dopo ": " o " - " (NON rompe "R-Type", "Pac-Man" ecc.)
        s = re.sub(r'\s*[:-]\s+.*$', '', s)
        s = re.sub(r'\b(the|a|an)\b\s*', '', s)
        return re.sub(r'\s+', ' ', s).strip()

    if core(r) == core(q):
        return 90

    r_words = r.split()
    q_words = q.split()

    # Result inizia con tutte le parole della query
    if r_words[:len(q_words)] == q_words:
        extra = r_words[len(q_words):]
        if not extra:
            return 100
        # Qualunque parola extra alla fine (sequel noti come "II", simboli come
        # "+", o markers mai visti prima) è trattata con la stessa cautela: non
        # possiamo enumerare ogni possibile marker di sequel/versione esistente,
        # quindi un default permissivo per gli "sconosciuti" è proprio ciò che
        # causa falsi positivi (es. "International Karate +" per query
        # "International Karate" — due giochi diversi, non un'edizione).
        return 30   # "Saboteur II" o "International Karate +" per query più corta

    # Query inizia con tutte le parole del result (result è prefisso della query)
    if q_words[:len(r_words)] == r_words:
        return 75

    # Tutte le parole della query presenti nel result, ma con parole extra sparse
    # ("Super R-Type" o "Space Trap" per query "R-Type"/"Trap"): stessa logica,
    # non fidarsi di più delle parole extra solo perché non le riconosciamo.
    q_set = set(q_words)
    r_set = set(r_words)
    if q_set.issubset(r_set):
        return 20   # "Super R-Type" per "R-Type", "Space Trap" per "Trap"

    # Match per sottostringa, ma solo a livello di parola intera — non un
    # frammento dentro una parola composta ("test" non deve matchare dentro
    # "super-test", che con split() resta un unico token per via del trattino)
    if len(q_words) == 1:
        if q_words[0] in r_words:
            return 35
    else:
        n = len(q_words)
        if any(r_words[i:i + n] == q_words for i in range(len(r_words) - n + 1)):
            return 35

    return 5


# Soglie di accettazione per _title_match_score
_SCORE_MIN_C64 = 35       # Giochi C64: accetta anche risultati parziali
_SCORE_MIN_FALLBACK = 75  # Fallback senza filtro C64: solo match molto precisi


class RAWGGameImages:
    def __init__(self, api_key, images_dir):
        """Inizializza il client RAWG.io con filtro per Commodore 64"""
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"
        self.images_dir = Path(images_dir)
        self.c64_platform_id = 15

    def clean_game_name(self, game_name):
        """Pulisce il nome del gioco rimuovendo metadati tecnici non utili alla ricerca."""
        import re

        if game_name.lower().endswith('.sid'):
            game_name = game_name[:-4]

        game_name = game_name.replace('_', ' ')

        patterns = [
            r'\s*\(\d{4}\)\s*$',
            r'\s*\d{4}\s*$',
            r'\s*\[.*?\]\s*$',
            r'\s*\(.*?version.*?\)\s*$',
            r'\s*(remix|version|demo|beta|alpha|unreleased)\s*$',
            r'\s*\d{2}\s*$',
            r'\s*(c64|commodore|sid)\s*$',
        ]

        for pattern in patterns:
            game_name = re.sub(pattern, '', game_name, flags=re.IGNORECASE)

        return re.sub(r'\s+', ' ', game_name).strip()

    def search_game_c64_only(self, game_name):
        """
        Cerca su RAWG con più varianti del nome e filtro C64.
        Ordine: varianti con filtro C64 → prima variante senza filtro.
        """
        if not HAS_REQUESTS:
            return None

        variants = _generate_name_variants(game_name)
        debug_print(f"RAWG: varianti di ricerca per '{game_name}': {variants}")

        # 1. Ogni variante CON filtro C64
        for variant in variants:
            result = self._do_search(variant, c64_only=True)
            if result:
                debug_print(f"RAWG: trovato '{result['name']}' per variante '{variant}'")
                return result

        # 2. Prima variante SENZA filtro C64 (giochi con tagging C64 incompleto)
        result = self._do_search(variants[0], c64_only=False)
        if result:
            debug_print(f"RAWG: trovato '{result['name']}' (senza filtro C64) per '{variants[0]}'")
        return result

    def _do_search(self, game_name, c64_only=True):
        """Esegue una singola ricerca RAWG e restituisce il miglior risultato."""
        params = {
            'key': self.api_key,
            'search': game_name,
            'page_size': 10,
            'ordering': '-rating',
        }
        if c64_only:
            params['platforms'] = self.c64_platform_id

        try:
            response = requests.get(f"{self.base_url}/games", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get('results', [])

            # Separa e ordina per score di corrispondenza titolo
            c64, other = [], []
            for game in results:
                pids = [p['platform']['id'] for p in game.get('platforms', [])]
                score = _title_match_score(game.get('name', ''), game_name)
                if self.c64_platform_id in pids:
                    c64.append((game, score))
                else:
                    other.append((game, score))

            c64.sort(key=lambda x: (-x[1], -bool(x[0].get('background_image'))))
            other.sort(key=lambda x: (-x[1], -bool(x[0].get('background_image'))))

            # Giochi C64 sopra la soglia minima, con immagine prima
            for game, score in c64:
                if score >= _SCORE_MIN_C64 and game.get('background_image'):
                    debug_print(f"RAWG C64 con img: '{game['name']}' score={score}")
                    return game
            for game, score in c64:
                if score >= _SCORE_MIN_C64:
                    debug_print(f"RAWG C64 senza img: '{game['name']}' score={score}")
                    return game

            # Fallback non-C64: solo se score alto (evita giochi sbagliati)
            if not c64_only:
                for game, score in other:
                    if score >= _SCORE_MIN_FALLBACK and game.get('background_image'):
                        debug_print(f"RAWG non-C64 (fallback): '{game['name']}' score={score}")
                        return game

            return None
        except Exception as e:
            debug_print(f"Errore RAWG per '{game_name}': {e}")
            return None

    def download_game_image(self, game_name, sid_filename=None):
        """Scarica l'immagine del gioco corrispondente al titolo."""
        if not HAS_REQUESTS:
            return None

        game_name_clean = self.clean_game_name(game_name)
        debug_print(f"Ricerca su RAWG (solo C64) per: '{game_name_clean}' (da: '{game_name}')")
        game = self.search_game_c64_only(game_name_clean)

        if not game:
            debug_print(f"Gioco C64 non trovato su RAWG: {game_name_clean}")
            return None

        platform_names = [p['platform']['name'] for p in game['platforms']]
        c64_platforms = ['Commodore / Amiga', 'Commodore 64', 'C64']
        has_c64 = any(c64 in str(p) for c64 in c64_platforms for p in platform_names)

        if not has_c64:
            debug_print(f"AVVISO: Gioco {game['name']} non è per C64. Piattaforme: {platform_names}")
            return None

        image_url = None
        if game.get('background_image'):
            image_url = game['background_image']
            debug_print(f"Trovata immagine per {game['name']} (C64 confermato)")

        if not image_url:
            debug_print(f"Nessuna immagine disponibile per {game['name']}")
            return None

        safe_game_name = _sanitize_filename(game['name'])
        if not safe_game_name:
            if sid_filename:
                safe_game_name = sid_filename.replace('.sid', '').replace('.SID', '')
            else:
                safe_game_name = game_name_clean

        output_filename = f"{safe_game_name}.jpg"
        output_path = self.images_dir / output_filename

        if output_path.exists():
            debug_print(f"Immagine già presente in cache: {output_path}")
            return str(output_path)

        try:
            debug_print(f"Download immagine da: {image_url[:80]}...")
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()

            self.images_dir.mkdir(exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            debug_print(f"Immagine C64 scaricata e salvata in: {output_path}")
            return str(output_path)
        except Exception as e:
            debug_print(f"Errore download immagine per {game['name']}: {e}")
            if output_path.exists():
                output_path.unlink()
            return None


class IGDBGameImages:
    def __init__(self, client_id, access_token, images_dir):
        """Inizializza il client IGDB per copertine C64"""
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.igdb.com/v4"
        self.images_dir = Path(images_dir)
        self.c64_platform_id = 15

    def clean_game_name(self, game_name):
        """Pulisce il nome del gioco rimuovendo metadati tecnici non utili alla ricerca."""
        import re

        if game_name.lower().endswith('.sid'):
            game_name = game_name[:-4]

        game_name = game_name.replace('_', ' ')

        patterns = [
            r'\s*\(\d{4}\)\s*$',
            r'\s*\d{4}\s*$',
            r'\s*\[.*?\]\s*$',
            r'\s*\(.*?version.*?\)\s*$',
            r'\s*(remix|version|demo|beta|alpha|unreleased)\s*$',
            r'\s*\d{2}\s*$',
            r'\s*(c64|commodore|sid)\s*$',
        ]
        # Nota: rimosso r'\s*-\s*.*$' perché tagliava titoli tipo "Out Run - Special"

        for pattern in patterns:
            game_name = re.sub(pattern, '', game_name, flags=re.IGNORECASE)

        return re.sub(r'\s+', ' ', game_name).strip()

    def search_game_c64_only(self, game_name):
        """
        Cerca su IGDB con più varianti del nome e filtro C64.
        Ordine: varianti con filtro C64 → prima variante senza filtro.
        """
        if not HAS_REQUESTS:
            return None

        variants = _generate_name_variants(game_name)
        debug_print(f"IGDB: varianti di ricerca per '{game_name}': {variants}")

        # 1. Ogni variante CON filtro C64
        for variant in variants:
            result = self._do_search(variant, c64_only=True)
            if result:
                debug_print(f"IGDB: trovato '{result.get('name')}' per variante '{variant}'")
                return result

        # 2. Prima variante SENZA filtro C64
        result = self._do_search(variants[0], c64_only=False)
        if result:
            debug_print(f"IGDB: trovato '{result.get('name')}' (senza filtro C64) per '{variants[0]}'")
        return result

    def _do_search(self, game_name, c64_only=True):
        """Esegue una singola ricerca IGDB e restituisce il miglior risultato."""
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json',
        }
        limit = 10 if c64_only else 5
        # Se c64_only=True, filtra server-side per platform C64 (id=15)
        where_clause = 'where platforms = (15); ' if c64_only else ''
        body = f'fields name, cover.*, platforms.*; search "{game_name}"; {where_clause}limit {limit};'

        try:
            debug_print(f"IGDB query: '{game_name}' (c64_only={c64_only})")
            response = requests.post(f"{self.base_url}/games", headers=headers, data=body, timeout=15)

            if response.status_code == 401:
                debug_print("ERRORE 401: Access Token IGDB non valido o scaduto!")
                return None
            elif response.status_code == 403:
                debug_print("ERRORE 403: Client ID non autorizzato")
                return None
            elif response.status_code != 200:
                debug_print(f"ERRORE IGDB {response.status_code}")
                return None

            games = response.json()
            if not games:
                return None

            # Separa C64 e altri, calcola score su tutti
            c64, other = [], []
            for game in games:
                pids = []
                for p in game.get('platforms', []):
                    if isinstance(p, dict):
                        pids.append(p.get('id'))
                    elif isinstance(p, int):
                        pids.append(p)
                score = _title_match_score(game.get('name', ''), game_name)
                if self.c64_platform_id in pids:
                    c64.append((game, score))
                else:
                    other.append((game, score))

            c64.sort(key=lambda x: (-x[1], -('cover' in x[0])))
            other.sort(key=lambda x: (-x[1], -('cover' in x[0])))
            debug_print(f"IGDB: {len(c64)} C64 su {len(games)} per '{game_name}'")

            # Giochi C64 sopra soglia, con copertina prima
            for game, score in c64:
                if score >= _SCORE_MIN_C64 and 'cover' in game:
                    debug_print(f"IGDB C64 con cover: '{game.get('name')}' score={score}")
                    return game
            for game, score in c64:
                if score >= _SCORE_MIN_C64:
                    debug_print(f"IGDB C64 senza cover: '{game.get('name')}' score={score}")
                    return game

            # Fallback non-C64: solo score alto (evita giochi sbagliati)
            if not c64_only:
                for game, score in other:
                    if score >= _SCORE_MIN_FALLBACK and 'cover' in game:
                        debug_print(f"IGDB non-C64 (fallback): '{game.get('name')}' score={score}")
                        return game

            return None

        except requests.exceptions.Timeout:
            debug_print(f"Timeout IGDB per '{game_name}'")
            return None
        except Exception as e:
            debug_print(f"Errore IGDB per '{game_name}': {type(e).__name__} - {e}")
            return None

    def get_cover_url(self, cover_data):
        """
        Costruisce l'URL della copertina da IGDB.
        cover_data può essere:
          - dict con 'image_id' (query cover.* completo)
          - int (solo ID del record cover, richiede /covers endpoint)
        """
        if not cover_data:
            return None

        # Se è un oggetto cover completo con image_id
        if isinstance(cover_data, dict) and 'image_id' in cover_data:
            image_id = cover_data['image_id']
            return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

        # Se è solo l'ID intero del record cover, accetta per compatibilità
        # (sebbene non sia ideale, la query dovrebbe espandere cover.*)
        if isinstance(cover_data, int):
            debug_print(f"IGDB: cover restituito come ID intero ({cover_data}), non come oggetto espanso. Query subottimale?")
            # Non possiamo costruire URL senza image_id — richiederebbe altra query
            return None

        return None

    def download_game_image(self, game_name, sid_filename=None):
        """Scarica la COPERTINA del gioco C64 da IGDB."""
        if not HAS_REQUESTS:
            return None

        game_name_clean = self.clean_game_name(game_name)
        debug_print(f"Ricerca copertina su IGDB (solo C64) per: '{game_name_clean}' (da: '{game_name}')")
        game = self.search_game_c64_only(game_name_clean)

        if not game:
            debug_print(f"Gioco C64 non trovato su IGDB: {game_name_clean}")
            return None

        if 'cover' not in game:
            debug_print(f"Gioco {game.get('name', 'N/A')} non ha copertina su IGDB")
            return None

        cover_url = self.get_cover_url(game['cover'])
        if not cover_url:
            debug_print(f"Impossibile ottenere URL copertina per {game.get('name', 'N/A')}")
            return None

        debug_print(f"Trovata copertina C64 per: {game.get('name', 'N/A')}")

        safe_game_name = _sanitize_filename(game.get('name', game_name_clean))
        output_filename = f"{safe_game_name}_COVER.jpg"
        output_path = self.images_dir / output_filename

        if output_path.exists():
            debug_print(f"Copertina già presente in cache: {output_path}")
            return str(output_path)

        try:
            debug_print(f"Download copertina da: {cover_url}")
            response = requests.get(cover_url, timeout=15)
            response.raise_for_status()

            self.images_dir.mkdir(exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(response.content)

            debug_print(f"Copertina C64 scaricata e salvata in: {output_path}")
            return str(output_path)
        except Exception as e:
            debug_print(f"Errore download copertina: {e}")
            if output_path.exists():
                output_path.unlink()
            return None


# ---------------------------------------------------------------------------
# AudioEngine: FIFO → sidplayfp → sounddevice con controllo volume
# ---------------------------------------------------------------------------

class AudioEngine:
    """
    Gestisce la riproduzione audio tramite named pipe (FIFO):
      sidplayfp scrive WAV sul FIFO → thread Python legge, applica volume,
      invia a sounddevice (CoreAudio su macOS).

    Se sounddevice non è disponibile, ricade sulla riproduzione diretta
    tramite subprocess (senza controllo volume).
    """

    def __init__(self, initial_volume=0.7):
        # volume: float 0.0–1.0, scritto dal main thread, letto dal thread audio
        self.volume = initial_volume
        self.output_device = None   # None = device di default del sistema
        self._stop_event = threading.Event()
        self._thread = None
        self._process = None
        self._fifo_path = None

    # ------------------------------------------------------------------
    # API pubblica
    # ------------------------------------------------------------------

    def play(self, sid_path, subsong, sidplay_cmd, on_done_callback=None):
        """
        Avvia la riproduzione di sid_path (subsong indicato).
        on_done_callback viene chiamato sul thread audio quando la traccia
        finisce naturalmente (NON se stop() è stato chiamato).
        Lancia FileNotFoundError se sidplay_cmd non esiste nel PATH.
        """
        self.stop()  # ferma l'eventuale traccia precedente
        self._stop_event.clear()

        if HAS_SOUNDDEVICE and HAS_FIFO:
            # macOS / Linux: streaming via FIFO con controllo volume
            self._play_via_fifo(sid_path, subsong, sidplay_cmd, on_done_callback)
        elif HAS_SOUNDDEVICE and not HAS_FIFO:
            # Windows con sounddevice: volume controllato tramite file temporaneo
            self._play_via_tempfile(sid_path, subsong, sidplay_cmd, on_done_callback)
        else:
            # Fallback: riproduzione diretta senza controllo volume
            self._play_direct(sid_path, subsong, sidplay_cmd, on_done_callback)

    def stop(self):
        """Ferma immediatamente la riproduzione."""
        self._stop_event.set()

        if self._process:
            try:
                # Se il processo è in pausa (SIGSTOP), riprendilo prima di terminarlo
                if HAS_PROCESS_PAUSE:
                    try:
                        self._process.send_signal(signal.SIGCONT)
                    except:
                        pass
                self._process.terminate()
                self._process.wait(timeout=2)
            except:
                pass
            self._process = None

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None

        self._cleanup_fifo()

    def pause(self):
        """Sospende la riproduzione via SIGSTOP (solo Unix/macOS)."""
        if not HAS_PROCESS_PAUSE:
            return False
        if self._process and self._process.poll() is None:
            try:
                self._process.send_signal(signal.SIGSTOP)
                return True
            except (ProcessLookupError, PermissionError, OSError):
                pass
        return False

    def resume(self):
        """Riprende la riproduzione via SIGCONT (solo Unix/macOS)."""
        if not HAS_PROCESS_PAUSE:
            return False
        if self._process and self._process.poll() is None:
            try:
                self._process.send_signal(signal.SIGCONT)
                return True
            except (ProcessLookupError, PermissionError, OSError):
                pass
        return False

    @property
    def is_active(self):
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Riproduzione via FIFO + sounddevice (con volume)
    # ------------------------------------------------------------------

    def _build_cmd(self, sidplay_cmd, subsong, extra_flag, sid_path):
        """Costruisce la lista di argomenti per sidplayfp."""
        cmd = [sidplay_cmd, f"-os{subsong}"]
        if extra_flag:
            cmd.append(extra_flag)
        cmd.append(sid_path)
        return cmd

    def _play_via_fifo(self, sid_path, subsong, sidplay_cmd, on_done_callback):
        # sidplayfp aggiunge automaticamente .wav al nome del file
        fifo_base = os.path.join(tempfile.gettempdir(), f"sidplayer_{os.getpid()}")
        fifo_path = fifo_base + ".wav"

        try:
            if os.path.exists(fifo_path):
                os.unlink(fifo_path)
            os.mkfifo(fifo_path)  # Solo Unix/macOS — HAS_FIFO è già verificato in play()
        except OSError as e:
            log_message(f"Errore creazione FIFO: {e}. Fallback riproduzione diretta.")
            self._play_direct(sid_path, subsong, sidplay_cmd, on_done_callback)
            return

        self._fifo_path = fifo_path

        # -w<base> → sidplayfp scrive su <base>.wav (la nostra FIFO)
        # -os<subsong> → subsong specifico in modalità single
        try:
            self._process = subprocess.Popen(
                self._build_cmd(sidplay_cmd, subsong, f"-w{fifo_base}", sid_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self._cleanup_fifo()
            raise

        self._thread = threading.Thread(
            target=self._stream_audio,
            args=(fifo_path, on_done_callback),
            daemon=True,
            name="SIDStream",
        )
        self._thread.start()

    def _stream_audio(self, fifo_path, on_done_callback):
        """Thread: legge PCM dal FIFO, applica volume, invia a CoreAudio."""
        try:
            f = open(fifo_path, "rb")
            channels, rate, bits = self._parse_wav_header(f)
            log_message(f"Audio stream: {rate}Hz {channels}ch {bits}bit")

            bytes_per_frame = channels * (bits // 8)
            chunk_frames = 2048
            chunk_bytes = chunk_frames * bytes_per_frame

            with sd.OutputStream(samplerate=rate, channels=channels, dtype="float32",
                                  device=self.output_device) as stream:
                while not self._stop_event.is_set():
                    raw = f.read(chunk_bytes)
                    if not raw:
                        break
                    # Pad eventuale chunk finale incompleto
                    if len(raw) % (bits // 8) != 0:
                        raw = raw + b"\x00" * (len(raw) % (bits // 8))
                    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    audio *= self.volume
                    stream.write(audio.reshape(-1, channels))

            f.close()

        except Exception as e:
            log_message(f"Errore audio stream: {e}")
        finally:
            self._cleanup_fifo()
            # Notifica fine naturale (non chiama callback se stop() è stato invocato)
            if not self._stop_event.is_set() and on_done_callback:
                try:
                    on_done_callback()
                except Exception as e:
                    log_message(f"Errore on_done_callback: {e}")

    def _parse_wav_header(self, f):
        """
        Legge l'header WAV e posiziona il file all'inizio dei dati PCM.
        Supporta header con chunk extra (es. LIST) prima di 'data'.
        """
        riff = f.read(12)
        if riff[:4] != b"RIFF" or riff[8:12] != b"WAVE":
            raise ValueError("Stream non è un WAV valido")

        channels, rate, bits = 1, 44100, 16

        while True:
            chunk_hdr = f.read(8)
            if len(chunk_hdr) < 8:
                break
            chunk_id = chunk_hdr[:4]
            chunk_size = struct.unpack_from("<I", chunk_hdr, 4)[0]

            if chunk_id == b"fmt ":
                fmt = f.read(chunk_size)
                channels = struct.unpack_from("<H", fmt, 2)[0]
                rate = struct.unpack_from("<I", fmt, 4)[0]
                bits = struct.unpack_from("<H", fmt, 14)[0]
            elif chunk_id == b"data":
                break  # posizionato all'inizio dei campioni PCM
            else:
                f.read(chunk_size)  # salta chunk sconosciuti

        return channels, rate, bits

    # ------------------------------------------------------------------
    # Fallback: riproduzione diretta senza controllo volume
    # ------------------------------------------------------------------

    def _play_direct(self, sid_path, subsong, sidplay_cmd, on_done_callback):
        """Riproduzione senza sounddevice: usa sidplayfp direttamente."""
        self._process = subprocess.Popen(
            self._build_cmd(sidplay_cmd, subsong, None, sid_path),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        def _monitor():
            self._process.wait()
            if not self._stop_event.is_set() and on_done_callback:
                try:
                    on_done_callback()
                except Exception as e:
                    log_message(f"Errore on_done_callback (direct): {e}")

        self._thread = threading.Thread(target=_monitor, daemon=True, name="SIDMonitor")
        self._thread.start()

    # ------------------------------------------------------------------
    # Windows: file temporaneo + sounddevice (nessuna FIFO disponibile)
    # ------------------------------------------------------------------

    def _play_via_tempfile(self, sid_path, subsong, sidplay_cmd, on_done_callback):
        """
        Windows: sidplayfp scrive su file WAV temporaneo, poi Python lo legge
        con controllo volume tramite sounddevice. Il rendering è in tempo reale:
        si inizia a leggere ogni 0.5s finché il file cresce, poi si riproduce.
        """
        tmp_base = os.path.join(tempfile.gettempdir(), f"sidplayer_{os.getpid()}")
        tmp_path = tmp_base + ".wav"
        self._fifo_path = tmp_path  # riuso _cleanup_fifo per la pulizia

        try:
            self._process = subprocess.Popen(
                self._build_cmd(sidplay_cmd, subsong, f"-w{tmp_base}", sid_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            self._fifo_path = None
            raise

        self._thread = threading.Thread(
            target=self._stream_tempfile,
            args=(tmp_path, on_done_callback),
            daemon=True,
            name="SIDStream-Win",
        )
        self._thread.start()

    def _stream_tempfile(self, tmp_path, on_done_callback):
        """Thread Windows: attende che sidplayfp scriva l'header, poi streamma."""
        import time

        # Attendi che il file esista e abbia almeno l'header WAV
        deadline = time.monotonic() + 10.0
        while not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 44:
            if self._stop_event.is_set() or time.monotonic() > deadline:
                self._cleanup_fifo()
                return
            time.sleep(0.05)

        try:
            f = open(tmp_path, 'rb')
            channels, rate, bits = self._parse_wav_header(f)
            log_message(f"Audio stream (tempfile): {rate}Hz {channels}ch {bits}bit")

            bytes_per_frame = channels * (bits // 8)
            chunk_frames = 2048
            chunk_bytes = chunk_frames * bytes_per_frame

            with sd.OutputStream(samplerate=rate, channels=channels, dtype="float32",
                                  device=self.output_device) as stream:
                while not self._stop_event.is_set():
                    raw = f.read(chunk_bytes)
                    if not raw:
                        # Controlla se sidplayfp è ancora in esecuzione
                        if self._process and self._process.poll() is not None:
                            break  # processo terminato, fine traccia
                        time.sleep(0.02)  # attendi altri dati
                        continue
                    if len(raw) % (bits // 8) != 0:
                        raw = raw + b"\x00" * (len(raw) % (bits // 8))
                    audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                    audio *= self.volume
                    stream.write(audio.reshape(-1, channels))
            f.close()
        except Exception as e:
            log_message(f"Errore audio stream (tempfile): {e}")
        finally:
            self._cleanup_fifo()
            if not self._stop_event.is_set() and on_done_callback:
                try:
                    on_done_callback()
                except Exception as e:
                    log_message(f"Errore on_done_callback (tempfile): {e}")

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def _cleanup_fifo(self):
        if self._fifo_path and os.path.exists(self._fifo_path):
            try:
                os.unlink(self._fifo_path)
            except:
                pass
        self._fifo_path = None


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Contatore nastro stile Datasette
# ---------------------------------------------------------------------------

class TapeCounter:
    """Tre cifre con animazione scorrimento verticale, stile contatore Datasette."""
    _DIGIT_H = 22
    _DIGIT_W = 16
    _PAD     = 4
    _FG      = "#b0afb4"
    _BG      = "#000000"
    _FONT    = ("Courier", 13, "bold")
    _ANIM_STEPS = 8
    _ANIM_MS    = 100   # ms per frame → 800 ms animazione totale
    _TICK_MS    = 2000  # ms per tick (~π×3cm / 4.76cm/s ≈ 1.98s)

    def __init__(self, parent, master_widget):
        self._master  = master_widget
        self.value    = 0
        self._running  = False
        self._tick_job = None
        self._anim_job = None
        w = 3 * self._DIGIT_W + 2 * self._PAD
        self.canvas = tk.Canvas(parent, width=w, height=self._DIGIT_H,
                                bg=self._BG, highlightthickness=1,
                                highlightbackground="#493e39")
        self._render(0, 0, 1.0)

    def _render(self, old_val, new_val, progress):
        self.canvas.delete("all")
        old_s = f"{old_val:03d}"
        new_s = f"{new_val:03d}"
        h = self._DIGIT_H
        for col in range(3):
            x = self._PAD + col * self._DIGIT_W + self._DIGIT_W // 2
            od, nd = old_s[col], new_s[col]
            if od == nd or progress >= 1.0:
                self.canvas.create_text(x, h // 2, text=nd,
                                        fill=self._FG, font=self._FONT,
                                        anchor="center")
            else:
                offset = int(progress * h)
                self.canvas.create_text(x, h // 2 - offset, text=od,
                                        fill=self._FG, font=self._FONT,
                                        anchor="center")
                self.canvas.create_text(x, h // 2 - offset + h, text=nd,
                                        fill=self._FG, font=self._FONT,
                                        anchor="center")

    def _animate(self, old_val, new_val, step):
        if step > self._ANIM_STEPS:
            self._render(new_val, new_val, 1.0)
            return
        self._render(old_val, new_val, step / self._ANIM_STEPS)
        self._anim_job = self._master.after(
            self._ANIM_MS, lambda: self._animate(old_val, new_val, step + 1))

    def _tick(self):
        if not self._running:
            return
        old_val    = self.value
        self.value = (self.value + 1) % 1000
        self._animate(old_val, self.value, 1)
        self._tick_job = self._master.after(self._TICK_MS, self._tick)

    def start(self):
        if not self._running:
            self._running = True
            self._tick()

    def pause(self):
        self._running = False
        if self._tick_job:
            self._master.after_cancel(self._tick_job)
            self._tick_job = None

    def reset(self):
        self._running = False
        for job in (self._tick_job, self._anim_job):
            if job:
                self._master.after_cancel(job)
        self._tick_job = self._anim_job = None
        self.value = 0
        self._render(0, 0, 1.0)


class TransportButton:
    """Tasto trasporto stile Datasette VC-1530: rettangolo nero verticale
    senza testo dentro; l'etichetta (parola sopra, simbolo sotto) vive
    invece su una striscia grigia separata sopra i tasti, come la targhetta
    RECORD/PLAY/REWIND/... stampata sulla scocca del device originale.

    tk.Button ignora bg/fg personalizzati su macOS (tema Aqua nativo), quindi
    il "tasto" è un tk.Label con binding sul click — stesso workaround già
    usato per SHUF e le frecce subsong. Espone .config(text=, state=) con la
    stessa firma di tk.Button per restare compatibile con le chiamate
    esistenti (self.buttons[N].config(...)) senza toccare il resto del codice.
    """
    _W, _H = 46, 62

    def __init__(self, legend_row, button_row, text, command, font_family):
        self.command = command  # None per i tasti decorativi (es. RECORD/EJECT)
        self._state = tk.NORMAL

        # Colonna etichetta, stessa larghezza/spaziatura della colonna tasto
        # sotto — così le due righe restano allineate pur vivendo in due
        # frame (e due sfondi) separati.
        # Altezza esplicita: senza, pack_propagate(False) blocca il frame
        # alla dimensione minima di default (quasi 0px) invece di adattarsi
        # al testo — l'etichetta risultava invisibile, non solo piccola.
        label_holder = tk.Frame(legend_row, width=self._W, height=26,
                                bg=TRANSPORT["LEGEND_BG"])
        label_holder.pack(side=tk.LEFT, padx=8, pady=(3, 2))
        label_holder.pack_propagate(False)

        self.label = tk.Label(label_holder, font=(font_family, 8, "bold"),
                               justify="center", pady=0,
                               fg=DATASETTE["TEXT"], bg=TRANSPORT["LEGEND_BG"])
        self.label.pack(expand=True)
        self._set_label_text(text)

        holder = tk.Frame(button_row, width=self._W, height=self._H,
                          bg=DATASETTE["PLASTIC"])
        holder.pack(side=tk.LEFT, padx=8, pady=4)
        holder.pack_propagate(False)

        self.btn = tk.Label(holder, bg=TRANSPORT["BTN"], relief="raised", bd=2)
        self.btn.pack(fill=tk.BOTH, expand=True)
        self.btn.bind("<ButtonPress-1>", self._on_press)
        self.btn.bind("<ButtonRelease-1>", self._on_release)

    def _set_label_text(self, text):
        # I chiamanti passano "simbolo\nparola" (stessa convenzione di prima,
        # quando il testo stava dentro il tasto) — qui si inverte per
        # mostrare la parola sopra e il simbolo sotto, come richiesto.
        parts = text.split("\n", 1)
        symbol, word = (parts[0], parts[1]) if len(parts) == 2 else ("", parts[0])
        self.label.config(text=f"{word}\n{symbol}")

    def _on_press(self, _event):
        if self._state == tk.NORMAL:
            self.btn.config(bg=TRANSPORT["BTN_ACT"], relief="sunken")

    def _on_release(self, _event):
        if self._state == tk.NORMAL:
            self.btn.config(bg=TRANSPORT["BTN"], relief="raised")
            if self.command:
                self.command()

    def config(self, text=None, state=None):
        if text is not None:
            self._set_label_text(text)
        if state is not None:
            self._state = state
            enabled = state == tk.NORMAL
            self.btn.config(bg=TRANSPORT["BTN"] if enabled else TRANSPORT["BTN_DIS"],
                            cursor="hand2" if enabled else "arrow")


# Player principale
# ---------------------------------------------------------------------------

class SidTkPlayer:
    def __init__(self, master, config=None):
        self.master = master

        # Carica la configurazione
        self.config = config if config else Config()

        # Imposta le proprietà dalla configurazione
        self.images_dir = self.config.images_dir
        self.playlist_file = self.config.playlist_file
        self.hvsc_root = self.config.hvsc_root
        self.gb64_boxart_path = self.config.gb64_boxart_path
        self.gb64_photos_path = self.config.gb64_photos_path
        self.sidplay_cmd = self.config.sidplay_cmd
        self.shuffle = self.config.shuffle
        self.font_family = self.config.font_family

        # Imposta la finestra
        self.master.title("SIDPLAYER C64")
        self.master.configure(bg=DATASETTE["PLASTIC"])
        self.master.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.master.resizable(self.config.window_resizable, self.config.window_resizable)
        self.master.protocol("WM_DELETE_WINDOW", self.quit_all)

        # API RAWG
        self.rawg_api_key = self.config.rawg_api_key
        self.rawg_fetcher = None
        if self.rawg_api_key and HAS_REQUESTS:
            self.rawg_fetcher = RAWGGameImages(self.rawg_api_key, self.images_dir)
            debug_print("Supporto RAWG.io attivato (solo C64) - basato su metadata SID")

        # API IGDB
        self.igdb_client_id = self.config.igdb_client_id
        self.igdb_access_token = self.config.igdb_access_token
        self.igdb_fetcher = None
        if self.igdb_client_id and self.igdb_access_token and HAS_REQUESTS:
            self.igdb_fetcher = IGDBGameImages(self.igdb_client_id, self.igdb_access_token, self.images_dir)
            debug_print("Supporto IGDB attivato (copertine C64) - basato su metadata SID")

        # === STIL Reader ===
        self.stil_reader = STILReader(self.config.stil_path)
        if self.stil_reader.loaded:
            debug_print(f"✓ STIL caricato: {len(self.stil_reader.entries)} entry")
        else:
            debug_print("ℹ STIL non disponibile (i titoli SID usano header o nome file)")

        # === GB64 Database (cover art precisa, stile DeepSID) ===
        self.gb64_db = GB64Database(self.config.gb64_mdb_path)
        if self.gb64_db.loaded:
            debug_print("✓ Database GB64 caricato")
        else:
            debug_print("ℹ Database GB64 non disponibile (cover cercate solo online)")

        if not self.rawg_fetcher and not self.igdb_fetcher:
            debug_print("ℹ Nessun servizio API attivato. Solo immagini locali.")

        debug_print(f"📁 Directory immagini: {self.images_dir}")
        debug_print("Priorità ricerca immagini: IGDB → RAWG → Locale (tramite metadata SID)")

        # === Audio Engine ===
        self.audio_engine = AudioEngine(initial_volume=0.7)

        # Dizionario per le PhotoImage dei bottoni PIL (evita GC)
        self._btn_imgs = {}

        # ---------------------------------------------------------------
        # UI
        # ---------------------------------------------------------------
        self.canvas = tk.Canvas(master, width=self.config.window_width, height=self.config.window_height,
                                bg=DATASETTE["PLASTIC"], highlightthickness=0)
        self.canvas.pack()

        # ---------------------------------------------------------------
        # Now Playing (macOS Control Center / Touch Bar)
        # ---------------------------------------------------------------
        self.now_playing = NowPlayingManager(
            master   = self.master,
            on_play  = self.play_pause_toggle,
            on_pause = self.play_pause_toggle,
            on_next  = self.skip_track,
            on_prev  = self.prev_track,
            on_stop  = self.stop_playlist,
        )
        if HAS_NOWPLAYING:
            log_message("Now Playing: integrazione macOS attiva")
            # Placeholder iniziale: evita che MTMR/Control Center mostrino "unknown"
            # prima che inizi la riproduzione. Viene sovrascritto da update() al play.
            self.now_playing.update(title="SIDPLAYER C64", artist="", is_playing=False)

        # ---------------------------------------------------------------
        # Header (y=0, h=32) — badge "commodore [strisce] 64" in stile
        # scocca originale, al posto della semplice scritta "SIDPLAYER
        # C64". Colori indicati dall'utente (non dalla palette standard
        # dell'app), font Courier fisso invece di self.font_family —
        # scelta voluta, per distinguerlo dal resto dell'interfaccia.
        # ---------------------------------------------------------------
        _header_bg = "#A28F7A"      # RAL 1019 Gray Beige — prova, alternativa RAL 7022 "#4C4A44"
        _header_text = "#E3CDBA"    # RGB(227,205,186)
        _header_stripes = ["#E8412C", "#F58220", "#FDB913", "#3AA35A", "#3FA9F5"]

        header_frame = tk.Frame(self.canvas, bg=_header_bg, height=32)
        header_frame.place(x=0, y=0, width=self.config.window_width)

        # Allineato a destra, in basso: pack(side=RIGHT) accumula da destra
        # verso sinistra, quindi si impacchetta in ordine inverso a quello
        # visivo voluto ("64" per primo, "commodore" per ultimo) — anchor="s"
        # per l'allineamento in basso nei 32px di altezza dell'header.
        tk.Label(header_frame, text="64", font=("Courier", 18, "bold"),
                 fg=_header_text, bg=_header_bg).pack(side=tk.RIGHT, padx=(8, 10), pady=2, anchor="s")

        _stripes_canvas = tk.Canvas(header_frame, width=90, height=22,
                                    bg=_header_bg, highlightthickness=0)
        _stripes_canvas.pack(side=tk.RIGHT, pady=5, anchor="s")
        _stripe_h = 22 / len(_header_stripes)
        for _i, _color in enumerate(_header_stripes):
            _y0 = _i * _stripe_h
            _stripes_canvas.create_rectangle(0, _y0, 90, _y0 + _stripe_h,
                                             fill=_color, outline="")

        tk.Label(header_frame, text="commodore", font=("Courier", 18, "bold"),
                 fg=_header_text, bg=_header_bg).pack(side=tk.RIGHT, padx=(20, 8), pady=2, anchor="s")

        # ---------------------------------------------------------------
        # Finestrella Datasette (y=40, h=330)
        # outer beige, inner scuro
        # ---------------------------------------------------------------
        outer_frame = tk.Frame(self.canvas,
                               bg=DATASETTE["BEZEL"],
                               highlightthickness=2,
                               highlightbackground=DATASETTE["BEZEL"],
                               highlightcolor=DATASETTE["BEZEL"])
        outer_frame.place(x=20, y=40, width=600, height=330)

        inner_frame = tk.Frame(outer_frame,
                               bg=DATASETTE["GLASS"],
                               highlightthickness=5,
                               highlightbackground=DATASETTE["SLOT"],
                               highlightcolor=DATASETTE["SLOT"])
        inner_frame.place(x=5, y=5, width=586, height=316)

        # Cover frame (sinistra, 180×180)
        self.cover_frame = tk.Frame(inner_frame, bg=DATASETTE["GLASS"])
        self.cover_frame.place(x=8, y=8, width=180, height=180)

        self.cover_placeholder = self._make_placeholder_image(180, 180)
        self.image_label = tk.Label(self.cover_frame,
                                    image=self.cover_placeholder,
                                    bg=DATASETTE["GLASS"])
        self.image_label.place(x=0, y=0, width=180, height=180)

        # Info frame (destra)
        info_frame = tk.Frame(inner_frame, bg=DATASETTE["GLASS"])
        info_frame.place(x=204, y=8, width=364, height=290)

        self.label_title = tk.Label(info_frame, text="LOAD & PLAY",
            font=(self.font_family, 16, "bold"), fg=C64_PALETTE["LIGHT_GREEN"],
            bg=DATASETTE["GLASS"], wraplength=360, justify="left", anchor="w")
        self.label_title.place(x=0, y=0, width=364)

        self.label_stil = tk.Label(info_frame, text="",
            font=(self.font_family, 9), fg=C64_PALETTE["CYAN"],
            bg=DATASETTE["GLASS"], wraplength=360, justify="left", anchor="w")
        self.label_stil.place(x=0, y=48, width=364)

        # Riga autore: nome + foto del musicista a destra (collezione GB64
        # locale, opzionale). La foto è nascosta di default, mostrata solo
        # se disponibile per l'autore corrente — sempre subito dopo il nome,
        # qualunque sia la sua lunghezza (pack, non coordinate fisse).
        self.author_row_frame = tk.Frame(info_frame, bg=DATASETTE["GLASS"])
        self.author_row_frame.place(x=0, y=70, width=364)

        self.label_author = tk.Label(self.author_row_frame, text="",
            font=(self.font_family, 10), fg=C64_PALETTE["CYAN"],
            bg=DATASETTE["GLASS"], wraplength=336, justify="left", anchor="w")
        self.label_author.pack(side=tk.LEFT)

        self.author_photo_image = None
        self.author_photo_label = tk.Label(self.author_row_frame, bg=DATASETTE["GLASS"])
        # non impacchettata qui: pack()/pack_forget() gestiti in _update_author_photo

        self.label_released = tk.Label(info_frame, text="",
            font=(self.font_family, 9), fg=C64_PALETTE["GREY"],
            bg=DATASETTE["GLASS"], wraplength=360, justify="left", anchor="w")
        self.label_released.place(x=0, y=96, width=364)

        self.label_track = tk.Label(info_frame, text="",
            font=(self.font_family, 9), fg=C64_PALETTE["YELLOW"],
            bg=DATASETTE["GLASS"], wraplength=360, justify="left", anchor="w")
        self.label_track.place(x=0, y=118, width=364)

        self.image_source_label = tk.Label(info_frame, text="",
            font=(self.font_family, 8), fg=C64_PALETTE["GREY"],
            bg=DATASETTE["GLASS"], wraplength=360, justify="left", anchor="w")
        self.image_source_label.place(x=0, y=140, width=364)

        # Subsong selector — visibile solo se il file ha più di un subsong
        self.subsong_frame = tk.Frame(info_frame, bg=DATASETTE["GLASS"])
        # non viene posizionato (place) finché non serve → invisibile di default

        self.btn_subsong_prev = tk.Label(
            self.subsong_frame, text="◄",
            font=(self.font_family, 9, "bold"),
            fg=C64_PALETTE["LIGHT_GREEN"], bg=DATASETTE["GLASS"],
            cursor="hand2")
        self.btn_subsong_prev.pack(side=tk.LEFT, padx=(0, 6))
        self.btn_subsong_prev.bind("<Button-1>", lambda e: self._change_subsong(-1))
        self.btn_subsong_prev.bind("<Enter>",
            lambda e: self.btn_subsong_prev.config(fg=C64_PALETTE["WHITE"]))
        self.btn_subsong_prev.bind("<Leave>",
            lambda e: self.btn_subsong_prev.config(fg=C64_PALETTE["LIGHT_GREEN"]))

        self.label_subsong = tk.Label(
            self.subsong_frame, text="",
            font=(self.font_family, 9), fg=C64_PALETTE["YELLOW"],
            bg=DATASETTE["GLASS"], anchor="center")
        self.label_subsong.pack(side=tk.LEFT, expand=True)

        self.btn_subsong_next = tk.Label(
            self.subsong_frame, text="►",
            font=(self.font_family, 9, "bold"),
            fg=C64_PALETTE["LIGHT_GREEN"], bg=DATASETTE["GLASS"],
            cursor="hand2")
        self.btn_subsong_next.pack(side=tk.LEFT, padx=(6, 0))
        self.btn_subsong_next.bind("<Button-1>", lambda e: self._change_subsong(+1))
        self.btn_subsong_next.bind("<Enter>",
            lambda e: self.btn_subsong_next.config(fg=C64_PALETTE["WHITE"]))
        self.btn_subsong_next.bind("<Leave>",
            lambda e: self.btn_subsong_next.config(fg=C64_PALETTE["LIGHT_GREEN"]))

        # Decorazione "AUTO STOP", centrata sull'intera finestrella, sopra il bordo
        # inferiore di inner_frame — creata per ultima cosi' resta in primo piano
        # rispetto a info_frame (altrimenti verrebbe coperta, essendo suo fratello
        # creato prima nello stesso genitore inner_frame)
        # Freccia stile Datasette: allineata dal secondo gambo della "U" (AUTO)
        # a poco prima della fine della "O" (STOP), appena sopra il testo
        autostop_canvas = tk.Canvas(inner_frame, width=100, height=50,
                                     bg=DATASETTE["GLASS"], highlightthickness=0)
        autostop_canvas.place(x=242, y=235)
        autostop_canvas.create_line(10, 30, 10, 40, 85, 40, 55, 22, 55, 30, 10, 30,
                                     fill=C64_PALETTE["LIGHT_GREY"], width=2,
                                     joinstyle=tk.ROUND, capstyle=tk.ROUND)

        autostop_label = tk.Label(inner_frame, text="AUTO  STOP",
                 font=(self.font_family, 11, "bold"),
                 fg=C64_PALETTE["LIGHT_GREY"], bg=DATASETTE["GLASS"],
                 justify=tk.CENTER, anchor="center")
        autostop_label.place(x=0, y=278, width=576, height=20)

        # ---------------------------------------------------------------
        # Utility row (y=378, h=36)
        # [LOAD] [OUT] [ABOUT]  spacer  [VOL label + slider + M]
        # ---------------------------------------------------------------
        util_frame = tk.Frame(self.canvas, bg=DATASETTE["PLASTIC"])
        util_frame.place(x=20, y=378, width=600, height=36)

        # Muted state init
        self._muted = False
        self._pre_mute_volume = 70

        self.buttons = [None] * 9  # 7 funzionali + RECORD/EJECT, slot 7/8

        def _make_utility_btn(parent, text, command):
            # tk.Button ignora bg/fg personalizzati su macOS (tema Aqua) —
            # tk.Label con binding, stesso workaround di SHUF e dei tasti
            # trasporto. Nessuno di questi tre va mai disabilitato, quindi
            # non serve un .config(state=) come su TransportButton.
            btn = tk.Label(parent, text=text,
                          font=(self.font_family, 10, "bold"),
                          fg=DATASETTE["TEXT"], bg=TRANSPORT["LEGEND_BG"],
                          relief="raised", bd=3, padx=6, pady=2,
                          cursor="hand2")

            def on_press(_e):
                btn.config(relief="sunken")

            def on_release(_e):
                btn.config(relief="raised")
                command()

            btn.bind("<ButtonPress-1>", on_press)
            btn.bind("<ButtonRelease-1>", on_release)
            return btn

        # Riassegnazione a catena (issue #36): LOAD si carica ora sul tasto
        # EJECT del trasporto (sempre fedele all'etichetta EJECT, cambia solo
        # l'azione al click); questi due slot prendono il posto lasciato
        # libero, uno ciascuno.
        btn_out = _make_utility_btn(util_frame, "OUT", self.show_audio_output_dialog)
        btn_out.pack(side=tk.LEFT, padx=(0, 4))
        self.buttons[0] = btn_out

        btn_help = _make_utility_btn(util_frame, "HELP", self.show_help)
        btn_help.pack(side=tk.LEFT, padx=(0, 4))
        self.buttons[1] = btn_help

        btn_about = _make_utility_btn(util_frame, "ABOUT", self.show_about)
        btn_about.pack(side=tk.LEFT, padx=(0, 8))
        self.buttons[2] = btn_about

        self.btn_shuffle = tk.Label(
            util_frame, text="", width=9, anchor="center",
            font=(self.font_family, 10, "bold"),
            bg=DATASETTE["PLASTIC"], relief="raised", bd=3, padx=6, pady=2,
        )
        self.btn_shuffle.pack(side=tk.LEFT, padx=(0, 8))
        self.btn_shuffle.bind("<Button-1>", lambda e: self._toggle_shuffle())
        self._update_shuffle_button()

        # Spacer
        tk.Frame(util_frame, bg=DATASETTE["PLASTIC"]).pack(side=tk.LEFT, expand=True, fill="x")

        # Volume
        tk.Label(util_frame, text="VOL",
                 font=(self.font_family, 9, "bold"),
                 fg=C64_PALETTE["DARK_GREY"],
                 bg=DATASETTE["PLASTIC"]).pack(side=tk.LEFT, padx=(0, 4))

        self.volume_var = tk.IntVar(value=70)
        self.volume_slider = tk.Scale(
            util_frame,
            from_=0, to=100,
            orient=tk.HORIZONTAL,
            variable=self.volume_var,
            command=self._on_volume_change,
            bg=DATASETTE["PLASTIC"],
            fg=C64_PALETTE["DARK_GREY"],
            troughcolor=C64_PALETTE["GREY"],
            activebackground=C64_PALETTE["CYAN"],
            highlightthickness=0,
            sliderrelief="flat",
            font=(self.font_family, 8),
            length=260,
            showvalue=True,
        )
        self.volume_slider.pack(side=tk.LEFT)

        self.mute_btn = tk.Button(
            util_frame, text="M",
            command=self._toggle_mute,
            font=(self.font_family, 9, "bold"),
            fg=C64_PALETTE["BLACK"],
            bg=C64_PALETTE["GREY"],
            activebackground=C64_PALETTE["RED"],
            relief="raised", bd=2, padx=4, pady=0,
        )
        self.mute_btn.pack(side=tk.LEFT, padx=(4, 0))

        # ---------------------------------------------------------------
        # Transport bar — badge Commodore in cima + tasti
        # ---------------------------------------------------------------
        transport_outer = tk.Frame(self.canvas,
                                   bg=DATASETTE["PLASTIC"],
                                   relief="ridge", bd=4)
        transport_outer.place(x=20, y=426, width=600, height=150)

        # Riga superiore: la "targhetta" nero+grigio non copre tutta la
        # larghezza come il resto (come nella foto del Datasette originale,
        # dove la placca è incassata nella scocca beige, non a tutta banda) —
        # inizia poco prima della "C=" e finisce poco prima del counter, che
        # sta fuori, sulla plastica beige.
        _badge_col = "#b0afb4"
        top_row = tk.Frame(transport_outer, height=79, bg=DATASETTE["PLASTIC"])
        top_row.pack(fill=tk.X, side=tk.TOP)
        top_row.pack_propagate(False)

        bar_plate = tk.Frame(top_row, width=380, height=79, bg=DATASETTE["PLASTIC"])
        # place() invece di pack(): il counter, impacchettato a destra nella
        # stessa riga, ridurrebbe la cavità disponibile e sposterebbe il
        # centro del pack — place() si centra sulla larghezza intera di
        # top_row, la stessa usata dal gruppo tasti sotto, restando allineati
        bar_plate.place(relx=0.5, y=0, anchor="n")
        bar_plate.pack_propagate(False)

        # Badge Commodore (nero). Contenuto ancorato in basso (anchor="s"):
        # l'altezza è più dell'ingombro naturale delle label, lo spazio in
        # più recuperato dalla striscia etichette sotto va tenuto in alto,
        # non distribuito attorno al contenuto.
        badge_frame = tk.Frame(bar_plate, height=47, bg=TRANSPORT["BG"])
        badge_frame.pack(fill=tk.X, side=tk.TOP)
        badge_frame.pack_propagate(False)

        tk.Label(badge_frame, text="C= commodore",
                 fg=_badge_col, bg=TRANSPORT["BG"],
                 font=(self.font_family, 13, "bold")).pack(side=tk.LEFT, padx=(12, 0), anchor="s")

        # Pannellino grigio con le barre nere. fill=Y invece di anchor="s":
        # il grigio riempie tutta l'altezza del badge, arrivando fino al
        # bordo inferiore alla stessa quota della striscia etichette sotto,
        # invece di essere solo alto quanto il testo.
        # Bordo nero solo sul lato destro: tk.Frame non supporta uno spessore
        # diverso per lato con highlightthickness (è uniforme sui 4 lati),
        # quindi si usa una striscia da 2px al posto giusto invece che un
        # bordo completo — niente bordo a sinistra/sopra/sotto, che
        # toccherebbero rispettivamente il nero del badge e il pannello sotto.
        bars_panel = tk.Frame(badge_frame, bg=TRANSPORT["BG"])
        bars_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(50, 0))
        tk.Frame(bars_panel, bg="#000000", width=2).pack(side=tk.RIGHT, fill=tk.Y)

        # fg era nero (bars su pannello grigio chiaro): con lo sfondo ora
        # scuro come il resto del badge, servono barre chiare per restare
        # visibili — stesso colore del testo "C= commodore" accanto.
        tk.Label(bars_panel, text="▉▊▋▌▍▎▏",
                 fg=_badge_col, bg=TRANSPORT["BG"],
                 font=("Courier", 34, "bold")).pack(expand=True, padx=(4, 2))

        # Striscia grigia con le etichette (parola+simbolo) — la targhetta
        # RECORD/PLAY/REWIND/... stampata sulla scocca, separata dai tasti
        # neri sotto: non deve avere lo sfondo beige della plastica.
        # Bordo nero su sinistra/destra/sotto, non sopra (tocca il pannello
        # barre sopra — stesso motivo delle strisce manuali sopra).
        legend_row = tk.Frame(bar_plate, height=32, bg=TRANSPORT["LEGEND_BG"])
        legend_row.pack(fill=tk.X, side=tk.TOP)
        legend_row.pack_propagate(False)
        tk.Frame(legend_row, bg="#000000", width=2).pack(side=tk.LEFT, fill=tk.Y)
        tk.Frame(legend_row, bg="#000000", width=2).pack(side=tk.RIGHT, fill=tk.Y)
        tk.Frame(legend_row, bg="#000000", height=2).pack(side=tk.BOTTOM, fill=tk.X)
        legend_group = tk.Frame(legend_row, bg=TRANSPORT["LEGEND_BG"])
        legend_group.pack(expand=True)

        # Counter, fuori dalla targhetta, sulla plastica beige a destra —
        # stessa fascia verticale (ancorato in basso), colori scuri invece
        # del grigio chiaro (pensato per contrasto su nero, non su beige)
        counter_frame = tk.Frame(top_row, bg=DATASETTE["PLASTIC"])
        counter_frame.pack(side=tk.RIGHT, padx=(0, 10), anchor="s")

        self.tape_counter = TapeCounter(counter_frame, self.master)
        self.tape_counter.canvas.pack(side=tk.TOP)

        # LED rosso accanto a "COUNTER": spento finché non si preme RECORD,
        # poi resta acceso. Riga separata (LED + testo) invece del solo
        # Label, così il gruppo si centra sotto la casella cifre come prima.
        counter_label_row = tk.Frame(counter_frame, bg=DATASETTE["PLASTIC"])
        counter_label_row.pack(side=tk.TOP)

        self._record_led_off = "#5a1414"
        self._record_led_on = "#ff2020"
        self.record_led_canvas = tk.Canvas(counter_label_row, width=7, height=7,
                                           bg=DATASETTE["PLASTIC"], highlightthickness=0)
        self.record_led_canvas.pack(side=tk.LEFT, padx=(0, 3))
        self.record_led = self.record_led_canvas.create_oval(
            1, 1, 6, 6, fill=self._record_led_off, outline="")

        tk.Label(counter_label_row, text="COUNTER",
                 fg=DATASETTE["TEXT"], bg=DATASETTE["PLASTIC"],
                 font=(self.font_family, 6, "bold")).pack(side=tk.LEFT)

        # Riga tasti: rettangoli neri su sfondo plastica beige (i tasti neri
        # non avrebbero contrasto su sfondo nero come il badge sopra)
        btn_row = tk.Frame(transport_outer, bg=DATASETTE["PLASTIC"])
        btn_row.pack(fill=tk.X, side=tk.TOP, expand=True)

        # Gruppo centrato (expand=True senza fill → si centra nello spazio
        # residuo, sia in orizzontale che in verticale, invece di restare
        # ancorato a sinistra). Stessa larghezza/spaziatura colonna della
        # riga legenda sopra, per restare allineati.
        btn_group = tk.Frame(btn_row, bg=DATASETTE["PLASTIC"])
        btn_group.pack(expand=True)

        # Ordine come sulla scocca originale: RECORD PLAY REWIND FFWD STOP EJECT.
        # RECORD salva su disco la playlist attualmente caricata (issue #36);
        # EJECT apre la stessa scelta file/playlist di LOAD, che ora sta qui
        # invece che nella riga utility — l'etichetta EJECT resta invariata,
        # fedele alla scocca originale, cambia solo l'azione al click.
        transport_specs = [
            ("●",  "RECORD", self.save_playlist_dialog, 7),
            ("▶",  "PLAY",   self.play_pause_toggle,     4),
            ("◄◄", "REWIND", self.prev_track,             3),
            ("▶▶", "FFWD",   self.skip_track,             5),
            ("■",  "STOP",   self.stop_playlist,          6),
            ("▲",  "EJECT",  self.load_files_dialog,     8),
        ]

        for symbol, label, cmd, slot_idx in transport_specs:
            btn = TransportButton(legend_group, btn_group, f"{symbol}\n{label}", cmd, self.font_family)
            self.buttons[slot_idx] = btn

        # RECORD disabilitato finché non ci sono tracce caricate (stesso
        # criterio di PLAY); EJECT parte abilitato, come LOAD prima di lui.
        self.buttons[7].config(state=tk.DISABLED)

        # ---------------------------------------------------------------
        # Stato applicazione
        # ---------------------------------------------------------------
        self.tracks = []
        self.track_subsongs = {}
        self.current_index = -1
        self.playing = False
        self.paused = False
        self.total_tracks = 0
        self.current_subsong = 1
        self.total_subsongs = 1
        self.current_image = None
        self.cover_placeholder  # già inizializzato sopra

        if not os.path.exists(self.images_dir):
            debug_print(f"AVVISO: Directory immagini non trovata: {self.images_dir}")
            os.makedirs(self.images_dir, exist_ok=True)

        # Stato iniziale bottoni transport: disabilitati (PLAY incluso,
        # finché non viene caricato almeno un SID o una playlist)
        self.buttons[3].config(state=tk.DISABLED)
        self.buttons[5].config(state=tk.DISABLED)
        self.buttons[6].config(state=tk.DISABLED)
        self._update_play_pause_button()

        # Boot screen: e' la prima cosa mostrata, e resta finche' non
        # succede qualcosa (playlist da cfg, LOAD manuale, o avvio riproduzione)
        self._show_boot_screen()

        # Carica automaticamente la playlist se esiste. Il caricamento è
        # istantaneo, ma un piccolo ritardo prima di mostrare la conferma fa
        # sì che il boot screen resti visibile un momento invece di sparire
        # in una frazione di secondo impercettibile.
        self.load_playlist_file()
        if self.total_tracks > 0:
            self.master.after(1500, self._confirm_playlist_autoloaded)

        self.update_status()

        # Porta la finestra in primo piano all'avvio (poi permette ad altre
        # finestre di tornare sopra, senza restare "always on top")
        self.master.lift()
        self.master.attributes("-topmost", True)
        self.master.after_idle(self.master.attributes, "-topmost", False)
        self.master.focus_force()

    def _make_placeholder_image(self, w, h):
        """Crea un'immagine placeholder C64-style con PIL."""
        img = Image.new('RGB', (w, h), '#000000')
        draw = ImageDraw.Draw(img)
        # Bordo verde
        draw.rectangle([0, 0, w-1, h-1], outline='#AAFF66', width=1)
        # Testo centrato
        _courier_path = (
            r"C:\Windows\Fonts\cour.ttf" if IS_WINDOWS
            else "/System/Library/Fonts/Supplemental/Courier New.ttf"
        )
        try:
            font_big  = ImageFont.truetype(_courier_path, 22)
            font_small = ImageFont.truetype(_courier_path, 13)
        except Exception:
            font_big  = ImageFont.load_default()
            font_small = font_big

        heart_text = "SID"
        no_img_text = "NO IMAGE"

        try:
            bb = draw.textbbox((0, 0), heart_text, font=font_big)
            tw = bb[2] - bb[0]
            draw.text(((w - tw) // 2, h // 2 - 26), heart_text, fill='#AAFF66', font=font_big)
            bb2 = draw.textbbox((0, 0), no_img_text, font=font_small)
            tw2 = bb2[2] - bb2[0]
            draw.text(((w - tw2) // 2, h // 2 + 4), no_img_text, fill='#FFFFFF', font=font_small)
        except Exception:
            draw.text((w//2 - 20, h//2 - 10), "NO IMG", fill='#AAFF66')

        return ImageTk.PhotoImage(img)

    def _restore_normal_fonts(self):
        """Ripristina font/geometria/allineamento normali delle label
        eventualmente modificate dalla schermata di boot."""
        self.label_title.place_forget()
        self.label_title.config(font=(self.font_family, 16, "bold"),
                                 anchor="w", justify="left")
        self.label_title.place(x=0, y=0, width=364)
        self.label_stil.place_forget()
        self.label_stil.place(x=0, y=48, width=364)
        self.label_released.place_forget()
        self.label_released.config(font=(self.font_family, 9))
        self.label_released.place(x=0, y=96, width=364)
        self.author_row_frame.place_forget()
        self.author_row_frame.place(x=0, y=70, width=364)

    def _show_boot_screen(self):
        """Easter egg: schermata di boot in stile C64 BASIC. È il primo stato
        mostrato all'avvio e resta finché non succede qualcosa — nessun
        timer, non e' una schermata "a tempo": la porta d'ingresso dell'app
        finché non viene caricato un SID/playlist o non parte la riproduzione.

        Titolo e riga RAM sono centrati (blocco unico su label_title, con le
        righe vuote nei punti giusti, come il vero messaggio ROM del C64).
        READY. e l'hint sotto sono invece allineati a sinistra — Tkinter non
        permette allineamenti diversi dentro la stessa label, quindi vivono
        su label separate (label_stil per READY., label_released per
        l'hint). Le posizioni si incatenano usando l'altezza *reale* di ogni
        label (winfo_reqheight, dopo update_idletasks) invece di un calcolo
        a mano sull'interlinea del font, che ignorerebbe il padding interno
        che Tkinter aggiunge di suo — altrimenti le righe si sovrappongono.
        """
        green = C64_PALETTE["LIGHT_GREEN"]
        boot_font = (self.font_family, 9)

        # Blocco centrato: titolo, riga vuota, RAM
        centered_text = (
            "**** COMMODORE 64 BASIC V2 ****\n"
            "\n"
            "64K RAM SYSTEM  38911 BASIC BYTES FREE\n"
            "\n"
        )
        self.label_title.place_forget()
        self.label_title.config(text=centered_text, fg=green, font=boot_font,
                                 anchor="n", justify="center")
        self.label_title.place(x=0, y=0, width=364)
        self.label_title.update_idletasks()
        y = self.label_title.winfo_reqheight()

        # READY., allineato a sinistra, subito sotto il blocco centrato
        self.label_stil.place_forget()
        self.label_stil.config(text="READY.", fg=green)
        self.label_stil.place(x=0, y=y, width=364)
        self.label_stil.update_idletasks()
        y += self.label_stil.winfo_reqheight()

        self.author_photo_label.pack_forget()
        self.label_author.config(text="")

        # Hint, allineato a sinistra, subito sotto READY. (nessuno spazio)
        self.label_released.place_forget()
        self.label_released.config(text="Click EJECT to select SID files or a playlist", fg=green,
                                    font=(self.font_family, 8))
        self.label_released.place(x=0, y=y, width=364)
        self.label_released.update_idletasks()
        y += self.label_released.winfo_reqheight()

        # Riga autore (usata anche per eventuali avvisi, es. "No files
        # found" se si preme PLAY senza aver caricato nulla): spostata
        # dinamicamente sotto l'hint, altrimenti resterebbe nella posizione
        # fissa del layout normale (y=70) e ci si sovrapporrebbe sopra.
        self.author_row_frame.place_forget()
        self.author_row_frame.place(x=0, y=y, width=364)

    def _confirm_playlist_autoloaded(self):
        """Sostituisce la schermata di boot con la conferma di caricamento,
        quando la playlist configurata in sidplayer.cfg viene caricata
        automaticamente all'avvio (chiamata solo se total_tracks > 0)."""
        if self.playing:
            return  # l'utente ha già premuto PLAY nel frattempo
        self._restore_normal_fonts()
        self.label_title.config(text="PLAYLIST LOADED", fg=C64_PALETTE["LIGHT_GREEN"])
        self.label_stil.config(text="", fg=C64_PALETTE["CYAN"])
        self.label_author.config(text=f"{self.total_tracks} files from playlist - Click PLAY",
                                  fg=C64_PALETTE["CYAN"])
        self.label_released.config(text="", fg=C64_PALETTE["GREY"])

    # ------------------------------------------------------------------
    # Play/Pause toggle
    # ------------------------------------------------------------------

    def _update_play_pause_button(self):
        """Aggiorna testo/simbolo di PLAY/PAUSE (buttons[4]) e lo stato di
        RECORD (buttons[7], abilitato solo con tracce caricate — stesso
        criterio di PLAY, chiamate sempre insieme nei punti dove cambia
        self.tracks)."""
        btn = self.buttons[4]
        if btn is None:
            return
        if not self.playing:
            btn.config(text="▶\nPLAY",
                       state=tk.NORMAL if self.tracks else tk.DISABLED)
        elif self.paused:
            btn.config(text="▶\nRESUME", state=tk.NORMAL)
        else:
            btn.config(text="⏸\nPAUSE",  state=tk.NORMAL)

        self.buttons[7].config(state=tk.NORMAL if self.tracks else tk.DISABLED)

    def play_pause_toggle(self):
        """Bottone PLAY/PAUSE unificato: avvia, mette in pausa o riprende."""
        if not self.playing:
            self.start_playlist()
            self.tape_counter.start()
        elif self.paused:
            if HAS_PROCESS_PAUSE:
                self.audio_engine.resume()
            self.paused = False
            self.tape_counter.start()
            self.now_playing.set_playing()
            self._update_play_pause_button()
            self.update_status()
        else:
            if HAS_PROCESS_PAUSE:
                self.audio_engine.pause()
            self.paused = True
            self.tape_counter.pause()
            self.now_playing.set_paused()
            self._update_play_pause_button()
            self.update_status()

    # ------------------------------------------------------------------
    # Volume
    # ------------------------------------------------------------------

    def _on_volume_change(self, val):
        """Aggiorna il volume dell'engine in tempo reale."""
        self.audio_engine.volume = int(val) / 100.0

    def _toggle_mute(self):
        """Muta/riattiva l'audio senza perdere il volume precedente."""
        if self._muted:
            self._muted = False
            self.volume_var.set(self._pre_mute_volume)
            self.audio_engine.volume = self._pre_mute_volume / 100.0
            self.mute_btn.config(bg=C64_PALETTE["GREY"], fg=C64_PALETTE["BLACK"])
        else:
            self._pre_mute_volume = self.volume_var.get()
            self._muted = True
            self.volume_var.set(0)
            self.audio_engine.volume = 0.0
            self.mute_btn.config(bg=C64_PALETTE["RED"], fg=C64_PALETTE["WHITE"])

    def _toggle_shuffle(self):
        """Attiva/disattiva lo shuffle per i prossimi caricamenti di playlist."""
        self.shuffle = not self.shuffle
        self._update_shuffle_button()

    def _update_shuffle_button(self):
        """Aggiorna testo e colore del bottone SHUF in base allo stato corrente."""
        if self.shuffle:
            self.btn_shuffle.config(text="SHUF: ON", fg=C64_PALETTE["LIGHT_GREEN"])
        else:
            self.btn_shuffle.config(text="SHUF: OFF", fg=C64_PALETTE["DARK_GREY"])

    # ------------------------------------------------------------------
    # Lettura metadata SID
    # ------------------------------------------------------------------

    def get_sid_title(self, sid_path):
        """Legge il titolo dall'header del file SID"""
        try:
            with open(sid_path, 'rb') as f:
                header = f.read(4)
                if header not in [b'PSID', b'RSID']:
                    return os.path.basename(sid_path).replace(".sid", "").replace("_", " ")

                f.seek(0x16)
                title_bytes = f.read(32)

                title = title_bytes.split(b'\x00')[0]
                title_text = title.decode('latin-1').strip()

                if not title_text or title_text.isspace():
                    return os.path.basename(sid_path).replace(".sid", "").replace("_", " ")
                return title_text
        except Exception as e:
            debug_print(f"Error reading SID title from {sid_path}: {e}")
            return os.path.basename(sid_path).replace(".sid", "").replace("_", " ")

    def get_sid_author(self, sid_path):
        """Legge l'autore dall'header del file SID"""
        try:
            with open(sid_path, 'rb') as f:
                header = f.read(4)
                if header not in [b'PSID', b'RSID']:
                    return "Unknown Author"

                f.seek(0x36)
                author_bytes = f.read(32)

                author = author_bytes.split(b'\x00')[0]
                author_text = author.decode('latin-1').strip()

                if not author_text or author_text.isspace():
                    return "Unknown Author"
                return author_text
        except Exception as e:
            debug_print(f"Error reading SID author from {sid_path}: {e}")
            return "Unknown Author"

    def get_sid_released(self, sid_path):
        """Legge il campo 'Released/Copyright' dall'header del file SID"""
        try:
            with open(sid_path, 'rb') as f:
                header = f.read(4)
                if header not in [b'PSID', b'RSID']:
                    return ""

                f.seek(0x56)
                released_bytes = f.read(32)

                released = released_bytes.split(b'\x00')[0]
                released_text = released.decode('latin-1').strip()

                if not released_text or released_text.isspace():
                    return ""
                return released_text
        except Exception as e:
            debug_print(f"Error reading SID released from {sid_path}: {e}")
            return ""

    def get_sid_songs(self, sid_path):
        """Legge il numero di subsong dall'header del file SID (offset 0x0E, 2 byte BE)."""
        try:
            with open(sid_path, 'rb') as f:
                header = f.read(4)
                if header not in [b'PSID', b'RSID']:
                    return 1
                f.seek(0x0E)
                data = f.read(2)
                if len(data) < 2:
                    return 1
                n = (data[0] << 8) | data[1]
                return max(1, n)
        except Exception:
            return 1

    def get_sid_default_song(self, sid_path):
        """Legge la subsong di default dall'header del file SID (offset 0x10, 2 byte BE)."""
        try:
            with open(sid_path, 'rb') as f:
                header = f.read(4)
                if header not in [b'PSID', b'RSID']:
                    return 1
                f.seek(0x10)
                data = f.read(2)
                if len(data) < 2:
                    return 1
                start_song = (data[0] << 8) | data[1]
                songs = self.get_sid_songs(sid_path)
                if start_song < 1 or start_song > songs:
                    return 1
                return start_song
        except Exception:
            return 1

    # ------------------------------------------------------------------
    # Subsong navigation
    # ------------------------------------------------------------------

    def _change_subsong(self, delta):
        """Passa al subsong precedente (delta=-1) o successivo (delta=+1), circolare."""
        if not self.playing or self.total_subsongs <= 1:
            return
        new_sub = ((self.current_subsong - 1 + delta) % self.total_subsongs) + 1
        self.current_subsong = new_sub
        self.track_subsongs[self.current_index] = new_sub
        # Riavvia la traccia corrente con il nuovo subsong
        self.current_index -= 1
        self.play_next_track()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def blink_title(self):
        current_fg = self.label_title.cget("fg")
        self.label_title.config(fg=C64_PALETTE["YELLOW"])
        self.master.after(200, lambda: self.label_title.config(fg=current_fg))

    def update_status(self):
        """Aggiorna label_track nella finestrella (rimossa la status bar in
        basso, ridondante con le informazioni già mostrate lì)."""
        if self.playing and self.total_tracks > 0:
            track_num = f"{self.current_index+1}/{self.total_tracks}"
            self.label_track.config(text=f"Track {track_num}")

    # ------------------------------------------------------------------
    # Caricamento file / playlist
    # ------------------------------------------------------------------

    def load_files_dialog(self):
        """Mostra un menu per scegliere cosa caricare: file SID o playlist"""
        dialog = tk.Toplevel(self.master)
        dialog.title("LOAD")
        dialog.configure(bg=C64_PALETTE["BLACK"])
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()

        title_label = tk.Label(dialog, text="Cosa vuoi caricare?",
                              font=(self.font_family, 14, "bold"),
                              fg=C64_PALETTE["LIGHT_GREEN"],
                              bg=C64_PALETTE["BLACK"])
        title_label.pack(pady=(20, 15))

        btn_frame = tk.Frame(dialog, bg=C64_PALETTE["BLACK"])
        btn_frame.pack(pady=(0, 20))

        def on_sid_files():
            dialog.destroy()
            self._load_sid_files()

        def on_playlist():
            dialog.destroy()
            self._load_playlist_dialog()

        btn_sid = tk.Button(btn_frame, text="SID FILES",
                           command=on_sid_files,
                           font=(self.font_family, 12, "bold"),
                           fg=C64_PALETTE["BLACK"],
                           bg=C64_PALETTE["LIGHT_BLUE"],
                           activebackground=C64_PALETTE["CYAN"],
                           activeforeground=C64_PALETTE["WHITE"],
                           relief="raised", bd=4, padx=15, pady=5)
        btn_sid.pack(side=tk.LEFT, padx=10)

        btn_playlist = tk.Button(btn_frame, text="PLAYLIST",
                                command=on_playlist,
                                font=(self.font_family, 12, "bold"),
                                fg=C64_PALETTE["BLACK"],
                                bg=C64_PALETTE["LIGHT_GREEN"],
                                activebackground=C64_PALETTE["CYAN"],
                                activeforeground=C64_PALETTE["WHITE"],
                                relief="raised", bd=4, padx=15, pady=5)
        btn_playlist.pack(side=tk.LEFT, padx=10)

        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (350 // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (180 // 2)
        dialog.geometry(f"350x180+{x}+{y}")

    def _load_track_list(self, files, via, append=False):
        """Imposta la lista di tracce e aggiorna la UI di conseguenza.

        Con append=True (LOAD/EJECT di file SID singoli) i file si
        aggiungono a quelli già caricati invece di sostituirli, senza
        duplicati per path: chi sceglie un SID alla volta sfogliando la
        libreria (invece di caricare una cartella intera) può così
        ritrovare con RECORD tutto quello ascoltato in sessione, non solo
        l'ultimo file scelto.

        current_index viene sempre riportato a -1: senza, se la riproduzione
        precedente era arrivata in fondo (o comunque current_index era
        rimasto più avanti della nuova lunghezza), il primo PLAY sulla
        lista appena caricata sforava subito la fine ("END OF PLAYLIST"
        immediato, STOP inutilizzabile perché self.playing non era mai
        diventato True)."""
        self.current_index = -1
        if append:
            new_files = [f for f in files if f not in self.tracks]
            start = len(self.tracks)
            self.tracks.extend(new_files)
            for i in range(start, len(self.tracks)):
                self.track_subsongs[i] = 1
        else:
            self.tracks = list(files)
            self.track_subsongs = {i: 1 for i in range(len(self.tracks))}
        self.total_tracks = len(self.tracks)
        self._restore_normal_fonts()
        self.label_title.config(text="FILES LOADED", fg=C64_PALETTE["LIGHT_GREEN"])
        self.label_stil.config(text="")
        self.label_author.config(text=f"{self.total_tracks} files - Click PLAY", fg=C64_PALETTE["CYAN"])
        self.label_released.config(text="", fg=C64_PALETTE["GREY"])
        self.blink_title()
        self.update_status()
        self._update_play_pause_button()
        log_message(f"Caricati {self.total_tracks} file SID {via}")

    def _load_sid_files(self):
        """Carica file SID selezionati dall'utente, aggiungendoli a quelli
        già caricati (vedi _load_track_list)."""
        files = filedialog.askopenfilenames(
            title="Select SID files",
            filetypes=[("SID files", "*.sid"), ("All files", "*.*")]
        )
        if files:
            self._load_track_list(files, "manualmente", append=True)

    def _load_playlist_from_path(self, file_path):
        """Carica una playlist da un path esplicito e aggiorna la UI di
        conseguenza. Restituisce True se il caricamento è riuscito."""
        original_playlist = self.playlist_file
        self.playlist_file = file_path

        ok = self.load_playlist_file()
        if ok:
            self._restore_normal_fonts()
            self.label_title.config(text="PLAYLIST LOADED", fg=C64_PALETTE["LIGHT_GREEN"])
            self.label_stil.config(text="")
            self.label_author.config(text=f"{self.total_tracks} files from playlist - Click PLAY",
                                      fg=C64_PALETTE["CYAN"])
            self.label_released.config(text="", fg=C64_PALETTE["GREY"])
            self.blink_title()
            self.update_status()
            log_message(f"Playlist caricata da: {file_path}")

        self.playlist_file = original_playlist
        return ok

    def _load_playlist_dialog(self):
        """Carica un file playlist selezionato dall'utente"""
        file_path = filedialog.askopenfilename(
            title="Select Playlist file",
            filetypes=[
                ("Playlist files", "*.txt *.cfg *.lst *.m3u *.pls"),
                ("All files", "*.*")
            ]
        )
        if file_path and not self._load_playlist_from_path(file_path):
            messagebox.showerror("Error", "Failed to load playlist")

    def save_playlist_dialog(self):
        """Salva su disco l'elenco delle tracce attualmente caricate come
        file playlist (tasto RECORD), nello stesso formato letto da
        load_playlist_file(). Chiede sempre il nome del file — nessun
        default 'playlist.txt', per non rischiare di sovrascrivere per
        sbaglio quella già configurata."""
        # update_idletasks() forza il redraw subito: senza, il cambio colore
        # resta in coda finché non si chiude il dialog bloccante sotto, e il
        # LED sembra accendersi solo alla chiusura invece che al click.
        self.record_led_canvas.itemconfig(self.record_led, fill=self._record_led_on)
        self.record_led_canvas.update_idletasks()

        try:
            if not self.tracks:
                return

            file_path = filedialog.asksaveasfilename(
                title="Save Playlist As",
                defaultextension=".txt",
                filetypes=[
                    ("Playlist files", "*.txt *.cfg *.lst *.m3u *.pls"),
                    ("All files", "*.*")
                ]
            )
            if not file_path:
                return

            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("# SIDPlayer Playlist\n")
                    f.write("# Formato: percorso_file.sid:traccia\n")
                    f.write("# Esempio: /Music/C64/song.sid:2\n\n")
                    for i, track_path in enumerate(self.tracks):
                        subsong = self.track_subsongs.get(i, 1)
                        f.write(f"{track_path}:{subsong}\n")
                log_message(f"Playlist salvata in: {file_path}")
            except Exception as e:
                log_message(f"Errore salvataggio playlist: {e}")
                messagebox.showerror("Error", f"Failed to save playlist: {e}")
        finally:
            # Spento appena la finestra di salvataggio si chiude, sia che
            # si sia salvato, annullato, o fallito.
            self.record_led_canvas.itemconfig(self.record_led, fill=self._record_led_off)

    def load_playlist_file(self):
        """Carica il file playlist se esiste."""
        playlist_path = self.playlist_file
        log_message(f"Cerco playlist: {playlist_path}")
        debug_print(f"📋 Cerco playlist: {playlist_path}")

        if not playlist_path or not os.path.exists(playlist_path):
            log_message("Playlist non trovata")
            debug_print("  ⚠ Playlist non trovata")
            return False

        try:
            with open(playlist_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            log_message(f"Errore lettura playlist: {e}")
            debug_print(f"  ⚠ Errore lettura playlist: {e}")
            return False

        if not lines:
            log_message("Playlist vuota")
            debug_print("  ⚠ Playlist vuota")
            return False

        expanded = [os.path.expanduser(os.path.expandvars(line)) for line in lines]
        if self.shuffle:
            random.shuffle(expanded)

        self.tracks = []
        self.track_subsongs = {}
        self.current_index = -1  # vedi commento in _load_track_list

        rank_prefix = re.compile(r'^\d+\.\s+')

        for i, entry in enumerate(expanded):
            # Formato "ranked" delle liste ufficiali HVSC, es. "  1. /Autore/Titolo.sid"
            entry = rank_prefix.sub('', entry)

            if ':' in entry:
                parts = entry.rsplit(':', 1)
                file_path = parts[0]
                try:
                    subsong = int(parts[1])
                except ValueError:
                    subsong = None
            else:
                file_path = entry
                subsong = None

            # Path HVSC-relativo (es. "/Autore/Titolo.sid"): risolvi contro hvsc_root
            # solo se il path assoluto letterale non esiste già sul filesystem
            if not os.path.exists(file_path) and self.hvsc_root and file_path.startswith('/'):
                hvsc_path = os.path.join(self.hvsc_root, file_path.lstrip('/'))
                if os.path.exists(hvsc_path):
                    file_path = hvsc_path

            if os.path.exists(file_path):
                self.tracks.append(file_path)
                if subsong is None:
                    subsong = self.get_sid_default_song(file_path)
                self.track_subsongs[len(self.tracks) - 1] = subsong

        self.total_tracks = len(self.tracks)

        log_message(f"Caricate {self.total_tracks} tracce dalla playlist")
        debug_print(f"  ✓ Caricate {self.total_tracks} tracce dalla playlist (randomizzate)")
        self._update_play_pause_button()
        return bool(self.tracks)

    # ------------------------------------------------------------------
    # Immagini
    # ------------------------------------------------------------------

    _IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']

    def _find_image_in_dir(self, directory, variants, suffixes=('',)):
        """Cerca un file immagine in una directory locale, provando ogni
        combinazione di variante/suffisso/estensione — prima match esatto,
        poi case-insensitive. Restituisce il path se trovato, altrimenti None."""
        if not directory or not os.path.isdir(directory):
            return None

        for variant in variants:
            for suffix in suffixes:
                for ext in self._IMAGE_EXTENSIONS:
                    path = os.path.join(directory, variant + suffix + ext)
                    if os.path.exists(path):
                        return path

        try:
            existing = os.listdir(directory)
        except OSError:
            return None
        existing_lower = {f.lower(): f for f in existing}

        for variant in variants:
            for suffix in suffixes:
                candidate_lower = (variant + suffix).lower()
                for ext in self._IMAGE_EXTENSIONS:
                    key = candidate_lower + ext
                    if key in existing_lower:
                        return os.path.join(directory, existing_lower[key])

        return None

    def find_game_image(self, sid_path, sid_title):
        """
        Cerca un'immagine per il gioco con strategia a cascata:
          1. Match locale nella cache di immagini già scaricate (esatto poi case-insensitive)
          2. Database GB64 (mdb), se configurato — match preciso per GA_Id
             invece che euristico per nome file (stesso approccio di DeepSID)
          3. API IGDB → RAWG (con varianti del nome)
        """
        file_name = os.path.basename(sid_path)

        safe_title = _sanitize_filename(sid_title)
        if not safe_title:
            safe_title = _sanitize_filename(file_name.replace('.sid', '').replace('.SID', ''))

        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir, exist_ok=True)

        # Genera varianti (es. "Elite Loader" → ["Elite Loader", "Elite"])
        raw_variants = _generate_name_variants(safe_title)
        local_variants = []
        seen = set()
        for v in raw_variants:
            sv = _sanitize_filename(v)
            if sv and sv not in seen:
                local_variants.append(sv)
                seen.add(sv)

        # 1. Cache locale delle immagini già scaricate in precedenza
        path = self._find_image_in_dir(self.images_dir, local_variants, suffixes=('', '_COVER'))
        if path:
            debug_print(f"Immagine locale: {os.path.basename(path)}")
            return path, "Local file"

        # 2. Database GB64: match preciso per GA_Id (nessuna chiamata di rete)
        if self.gb64_db.loaded and self.gb64_boxart_path:
            rel_path = self.gb64_db.find_cover_relpath(sid_title, _title_match_score, _SCORE_MIN_C64)
            if rel_path:
                path = os.path.join(self.gb64_boxart_path, rel_path)
                if os.path.exists(path):
                    debug_print(f"Immagine GB64 (db): {os.path.basename(path)}")
                    return path, "GB64 (DeepSID-style)"

        # 3. API: IGDB → RAWG (le classi gestiscono già le varianti internamente)
        if self.igdb_fetcher:
            debug_print(f"Provo IGDB per: '{sid_title}'")
            downloaded_path = self.igdb_fetcher.download_game_image(sid_title, file_name)
            if downloaded_path:
                return downloaded_path, "IGDB (C64 cover)"

        if self.rawg_fetcher:
            debug_print(f"Provo RAWG per: '{sid_title}'")
            downloaded_path = self.rawg_fetcher.download_game_image(sid_title, file_name)
            if downloaded_path:
                return downloaded_path, "RAWG.io (C64)"

        debug_print(f"Nessuna immagine trovata per: '{sid_title}'")
        return None, None

    def load_and_display_image(self, image_path, source):
        """Carica e mostra l'immagine ridimensionata nella finestrella (cover_frame)."""
        try:
            self.image_label.config(image='', text="")
            self.image_source_label.config(text="")
            if self.current_image:
                self.current_image = None

            img = Image.open(image_path)

            max_width = 180
            max_height = 180

            width_ratio = max_width / img.width
            height_ratio = max_height / img.height
            ratio = min(width_ratio, height_ratio)

            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image, bg=DATASETTE["GLASS"])

            if source:
                self.image_source_label.config(text=f"Img: {source}")

        except Exception as e:
            self.image_label.config(text=f"[Err]\n{os.path.basename(image_path)}",
                                    font=(self.font_family, 8),
                                    fg=C64_PALETTE["RED"],
                                    bg=DATASETTE["GLASS"])
            self.image_source_label.config(text="")

    _AUTHOR_PHOTO_SIZE = 22

    def _find_author_photo(self, author):
        """Cerca la foto del musicista nella collezione GB64 locale
        (opzionale). Se l'header elenca più autori ("Rob Hubbard & Jason
        Page"), prova anche solo il primo nome."""
        if not self.gb64_photos_path or not author:
            return None

        variants = [author]
        first_author = re.split(r'\s*[&,/]\s*', author)[0].strip()
        if first_author and first_author != author:
            variants.append(first_author)

        variants = [_sanitize_filename(v).replace(' ', '_') for v in variants]
        return self._find_image_in_dir(self.gb64_photos_path, variants)

    def _update_author_photo(self, author):
        """Mostra la foto del musicista subito a destra del nome se
        disponibile, altrimenti nasconde lo spazio (nessun placeholder: è
        un dettaglio secondario, non l'elemento visivo principale della
        finestrella)."""
        path = self._find_author_photo(author)

        if not path:
            self.author_photo_label.pack_forget()
            return

        try:
            img = Image.open(path).convert("RGB")
            size = self._AUTHOR_PHOTO_SIZE
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            self.author_photo_image = ImageTk.PhotoImage(img)
            self.author_photo_label.config(image=self.author_photo_image)
            self.author_photo_label.pack(side=tk.LEFT, padx=(6, 0))
        except Exception as e:
            debug_print(f"Errore caricamento foto musicista: {e}")
            self.author_photo_label.pack_forget()

    # ------------------------------------------------------------------
    # Controllo playlist
    # ------------------------------------------------------------------

    def start_playlist(self):
        if self.playing:
            return

        if not self.tracks:
            if self.load_playlist_file():
                self.label_author.config(text=f"{self.total_tracks} files from playlist.txt")
            else:
                self.label_author.config(text="No files found! Click EJECT first", fg=C64_PALETTE["RED"])
                return

        if not self.tracks:
            return

        self.playing = True
        self.paused = False
        self.buttons[8].config(state=tk.DISABLED)   # EJECT (carica file)
        self.buttons[3].config(state=tk.NORMAL)     # REWIND
        self.buttons[5].config(state=tk.NORMAL)     # FFWD
        self.buttons[6].config(state=tk.NORMAL)     # STOP
        self._update_play_pause_button()
        self.play_next_track()

    def stop_playlist(self):
        if not self.playing:
            return
        self.audio_engine.stop()
        self.tape_counter.reset()
        self.now_playing.clear()
        _np_clear()
        self.playing = False
        self.paused = False
        self.current_index = -1
        self.current_subsong = 1
        self.total_subsongs = 1
        self.subsong_frame.place_forget()
        self.label_title.config(text="STOPPED", fg=C64_PALETTE["RED"])
        self.label_stil.config(text="")
        self.label_author.config(text="")
        self.label_released.config(text="")
        self.label_track.config(text="")
        self.image_label.config(image=self.cover_placeholder, text="")
        self.image_source_label.config(text="")
        self._update_author_photo(None)
        self.buttons[8].config(state=tk.NORMAL)     # EJECT (carica file)
        self.buttons[3].config(state=tk.DISABLED)   # REWIND
        self.buttons[5].config(state=tk.DISABLED)   # FFWD
        self.buttons[6].config(state=tk.DISABLED)   # STOP
        self._update_play_pause_button()
        self.update_status()

    def play_next_track(self):
        # Ferma la traccia corrente (imposta stop_event → il callback non si attiva)
        self.audio_engine.stop()
        # Nel caso si stia ancora vedendo il boot screen (font ridotti)
        self._restore_normal_fonts()

        self.current_index += 1
        if self.current_index >= len(self.tracks):
            self.label_title.config(text="END OF PLAYLIST", fg=C64_PALETTE["CYAN"])
            self.label_stil.config(text="")
            self.label_author.config(text="All tracks completed")
            self.label_released.config(text="")
            self.label_track.config(text="")
            self.image_label.config(image=self.cover_placeholder, text="")
            self.image_source_label.config(text="")
            self._update_author_photo(None)
            self.tape_counter.reset()
            self.playing = False
            self.paused = False
            self.buttons[8].config(state=tk.NORMAL)     # EJECT (carica file)
            self.buttons[3].config(state=tk.DISABLED)   # REWIND
            self.buttons[5].config(state=tk.DISABLED)   # FFWD
            self.buttons[6].config(state=tk.DISABLED)   # STOP
            self._update_play_pause_button()
            self.update_status()
            return

        # Reset pausa all'inizio di ogni nuova traccia
        self.paused = False
        self._update_play_pause_button()

        track_path = self.tracks[self.current_index]
        if not os.path.exists(track_path):
            self.master.after(100, self.play_next_track)
            return

        subsong = self.track_subsongs.get(self.current_index, 1)
        self.current_subsong = subsong
        self.total_subsongs = self.get_sid_songs(track_path)

        # Metadata SID
        header_title = self.get_sid_title(track_path)
        author = self.get_sid_author(track_path)
        released = self.get_sid_released(track_path)

        stil_title = None
        if self.stil_reader.loaded:
            stil_title = self.stil_reader.get_title(track_path, subsong, fallback_to_filename=False)

        main_title = header_title

        self.label_title.config(text=main_title, fg=C64_PALETTE["LIGHT_GREEN"])

        if stil_title and stil_title != main_title:
            self.label_stil.config(text=stil_title, fg=C64_PALETTE["CYAN"])
            log_message(f"STIL subsong {subsong}: '{stil_title}'")
        else:
            self.label_stil.config(text="", fg=C64_PALETTE["CYAN"])

        author_text = f"by {author}" if author else ""
        self.label_author.config(text=author_text, fg=C64_PALETTE["CYAN"])
        self._update_author_photo(author)

        self.label_released.config(text=released if released else "", fg=C64_PALETTE["GREY"])

        # Aggiorna Now Playing (Control Center / Touch Bar) e file MTMR
        display_title = stil_title if (stil_title and stil_title != main_title) else main_title
        self.now_playing.update(title=display_title or "", artist=author or "", is_playing=True)
        # MTMR mostra sempre il nome del gioco (main_title), GUI mostra subsong se disponibile
        _np_write(author or "", main_title or "")

        track_text = f"Track {self.current_index + 1}/{self.total_tracks}"
        self.label_track.config(text=track_text, fg=C64_PALETTE["YELLOW"])

        # Subsong selector: mostra solo se il file ha più subsong
        if self.total_subsongs > 1:
            self.label_subsong.config(
                text=f"Subsong  {self.current_subsong} / {self.total_subsongs}")
            self.subsong_frame.place(x=0, y=162, width=364, height=22)
        else:
            self.subsong_frame.place_forget()

        self.blink_title()
        self.update_status()

        # Mostra placeholder immagine subito (non blocca l'avvio audio)
        self.current_image = None
        self.image_label.config(
            image=self.cover_placeholder,
            text="",
            bg=DATASETTE["GLASS"],
        )
        self.image_source_label.config(text="")

        # Avvia riproduzione subito, senza aspettare le immagini
        try:
            self.audio_engine.play(track_path, subsong, self.sidplay_cmd)
            log_message(f"Riproduzione: {track_path} (traccia {subsong})")
            if HAS_SOUNDDEVICE:
                log_message(f"Volume: {self.volume_var.get()}%")
        except FileNotFoundError:
            messagebox.showerror("Error", f"{self.sidplay_cmd} not found in PATH")
            self.stop_playlist()
            return

        # Fetch immagine in background: non blocca la riproduzione
        track_index_at_start = self.current_index

        def _fetch_image_bg():
            image_path, image_source = self.find_game_image(track_path, main_title)

            def _update_ui():
                # Scarta il risultato se nel frattempo è cambiata la traccia
                if self.current_index != track_index_at_start:
                    return
                if image_path:
                    self.load_and_display_image(image_path, image_source)
                else:
                    self.image_label.config(
                        image=self.cover_placeholder,
                        text="",
                        bg=DATASETTE["GLASS"],
                    )
                    self.image_source_label.config(text="")

            self.master.after(0, _update_ui)

        threading.Thread(target=_fetch_image_bg, daemon=True, name="ImageFetch").start()

        # Polling per avanzare alla traccia successiva (come check_track_done originale)
        self.master.after(500, lambda idx=self.current_index: self._poll_track_end(idx))

    def _poll_track_end(self, expected_index):
        """Polling ogni 500 ms: avanza traccia quando sidplayfp è terminato."""
        if not self.playing or self.current_index != expected_index:
            return  # Già avanzata (skip/stop) o playlist ferma
        if self.paused or self.audio_engine.is_active:
            self.master.after(500, lambda: self._poll_track_end(expected_index))
        else:
            # sidplayfp terminato e stream audio esaurito → prossima traccia
            self.play_next_track()

    def skip_track(self):
        if not self.playing:
            return
        if self.paused:
            self.paused = False
        self.play_next_track()

    def prev_track(self):
        """Torna al brano precedente (o risuona il primo se già al primo)."""
        if not self.playing:
            return
        if self.paused:
            self.paused = False
        # play_next_track farà += 1: per tornare all'indice N-1 impostiamo N-2.
        # Se siamo al primo brano (index=0), max(-1, -2)=-1 → play_next_track
        # riparte da 0 (riascolta il primo brano).
        self.current_index = max(-1, self.current_index - 2)
        self.play_next_track()

    # ------------------------------------------------------------------
    # About
    # ------------------------------------------------------------------

    def show_about(self):
        """Mostra la finestra About"""
        about_window = tk.Toplevel(self.master)
        about_window.title("About SIDPLAYER")
        about_window.configure(bg=C64_PALETTE["BLACK"])
        about_window.geometry("460x620")
        about_window.resizable(False, False)

        title_label = tk.Label(about_window, text="SIDPLAYER C64",
                              font=(self.font_family, 22, "bold"),
                              fg=C64_PALETTE["LIGHT_GREEN"],
                              bg=C64_PALETTE["BLACK"])
        title_label.pack(pady=(14, 2))

        version_label = tk.Label(about_window, text=VERSION,
                               font=(self.font_family, 12),
                               fg=C64_PALETTE["CYAN"],
                               bg=C64_PALETTE["BLACK"])
        version_label.pack(pady=(0, 10))

        # Ritratto autore
        portrait_image = None
        portrait_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "ezrad_portrait.png"),
            os.path.expanduser("~/Library/Application Support/SIDPlayer/ezrad_portrait.png"),
            "ezrad_portrait.png",
        ]
        for path in portrait_paths:
            if os.path.exists(path):
                try:
                    img = Image.open(path).convert("RGBA")
                    img = img.resize((160, 160), Image.Resampling.LANCZOS)
                    portrait_image = ImageTk.PhotoImage(img)
                    portrait_label = tk.Label(about_window, image=portrait_image,
                                              bg=C64_PALETTE["BLACK"])
                    portrait_label.image = portrait_image
                    portrait_label.pack(pady=(5, 6))
                except Exception as e:
                    log_message(f"Errore caricamento ritratto: {e}")
                break

        # Crediti in stile demoscene, allineati a colonna (font monospace)
        credits_label = tk.Label(about_window,
                                text=("CODE ............ EZRAD & IA\n"
                                      "MUSIC ........... HUBBARD, GALWAY, TEL,\n"
                                      "                  DAGLISH & THE SID LEGENDS\n"
                                      "SID CHIP ........ BOB YANNES, MOS 1982\n"
                                      "SPECIAL THANKS .. HVSC CREW"),
                                font=(self.font_family, 10),
                                fg=C64_PALETTE["WHITE"],
                                bg=C64_PALETTE["BLACK"],
                                justify="left")
        credits_label.pack(pady=(6, 10))

        greetings_label = tk.Label(about_window,
                                  text="GREETINGS TO ALL SID FANS WORLDWIDE",
                                  font=(self.font_family, 10, "bold"),
                                  fg=C64_PALETTE["LIGHT_GREEN"],
                                  bg=C64_PALETTE["BLACK"],
                                  wraplength=400, justify="center")
        greetings_label.pack(pady=(0, 10))

        # Separatore
        tk.Frame(about_window, bg=C64_PALETTE["GREY"], height=1).pack(fill=tk.X, padx=40)

        if self.stil_reader.loaded:
            stil_info = f"✓  STIL: {len(self.stil_reader.entries):,} entries — subsong titles enabled"
            stil_fg = C64_PALETTE["LIGHT_GREEN"]
        else:
            stil_info = "✗  STIL not available — using SID header titles"
            stil_fg = C64_PALETTE["GREY"]

        tk.Label(about_window, text=stil_info,
                 font=(self.font_family, 9), fg=stil_fg,
                 bg=C64_PALETTE["BLACK"],
                 wraplength=400, justify="center").pack(pady=(8, 2))

        vol_fg = C64_PALETTE["LIGHT_GREEN"] if HAS_SOUNDDEVICE else C64_PALETTE["GREY"]
        vol_info = ("✓  Volume control via FIFO + sounddevice" if HAS_SOUNDDEVICE
                    else "✗  Volume control unavailable — install sounddevice")
        tk.Label(about_window, text=vol_info,
                 font=(self.font_family, 9), fg=vol_fg,
                 bg=C64_PALETTE["BLACK"],
                 wraplength=400, justify="center").pack(pady=(2, 8))

        # Separatore
        tk.Frame(about_window, bg=C64_PALETTE["GREY"], height=1).pack(fill=tk.X, padx=40)

        tk.Label(about_window, text="github.com/ezradibiase",
                 font=(self.font_family, 9),
                 fg=C64_PALETTE["LIGHT_BLUE"],
                 bg=C64_PALETTE["BLACK"]).pack(pady=(10, 4))

        close_btn = tk.Button(about_window, text="CLOSE",
                             command=about_window.destroy,
                             font=(self.font_family, 12, "bold"),
                             fg=C64_PALETTE["BLACK"],
                             bg=C64_PALETTE["LIGHT_BLUE"],
                             padx=20, pady=5, anchor="center")
        close_btn.pack(pady=(15, 0))

        about_window.transient(self.master)
        about_window.grab_set()
        about_window.focus_set()

        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (460 // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (580 // 2)
        about_window.geometry(f"460x580+{x}+{y}")

    def show_help(self):
        """Mostra la finestra HELP: spiega i tasti trasporto meno ovvi
        (EJECT, PLAY, RECORD) — REWIND/FFWD/STOP sono già chiari dal nome."""
        help_window = tk.Toplevel(self.master)
        help_window.title("Help")
        help_window.configure(bg=C64_PALETTE["BLACK"])
        help_window.resizable(False, False)

        tk.Label(help_window, text="HELP",
                 font=(self.font_family, 22, "bold"),
                 fg=C64_PALETTE["LIGHT_GREEN"],
                 bg=C64_PALETTE["BLACK"]).pack(pady=(14, 12))

        entries = [
            ("▶  PLAY", "Starts playback. Once playback has started, the "
                        "same button pauses and resumes it."),
            ("●  RECORD", "Saves the list of currently loaded tracks to disk "
                          "as a new playlist file."),
            ("▲  EJECT", "Opens the file picker to load SID files or a "
                         "playlist."),
        ]
        for symbol, text in entries:
            tk.Label(help_window, text=symbol,
                     font=(self.font_family, 13, "bold"),
                     fg=C64_PALETTE["CYAN"], bg=C64_PALETTE["BLACK"]
                     ).pack(pady=(10, 3))
            tk.Label(help_window, text=text,
                     font=(self.font_family, 10),
                     fg=C64_PALETTE["WHITE"], bg=C64_PALETTE["BLACK"],
                     wraplength=380, justify="center").pack(padx=25)

        close_btn = tk.Button(help_window, text="CLOSE",
                             command=help_window.destroy,
                             font=(self.font_family, 12, "bold"),
                             fg=C64_PALETTE["BLACK"],
                             bg=C64_PALETTE["LIGHT_BLUE"],
                             padx=20, pady=5)
        close_btn.pack(pady=(20, 16))

        help_window.transient(self.master)
        help_window.grab_set()
        help_window.focus_set()

        help_window.update_idletasks()
        w, h = 440, help_window.winfo_reqheight()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (w // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (h // 2)
        help_window.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------

    def show_audio_output_dialog(self):
        """Mostra un popup per selezionare il device di output audio."""
        if not HAS_SOUNDDEVICE:
            return

        # Raccoglie i device di output disponibili
        try:
            all_devices = sd.query_devices()
        except Exception as e:
            log_message(f"Errore query devices: {e}")
            return

        output_devices = []  # lista di (indice_sd, nome)
        for i, dev in enumerate(all_devices):
            if dev["max_output_channels"] > 0:
                output_devices.append((i, dev["name"]))

        if not output_devices:
            return

        # Finestra popup
        dlg = tk.Toplevel(self.master)
        dlg.title("Audio Output")
        dlg.configure(bg=C64_PALETTE["BLACK"])
        dlg.resizable(False, False)
        dlg.transient(self.master)
        dlg.grab_set()

        w, h = 420, 320
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (w // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (h // 2)
        dlg.geometry(f"{w}x{h}+{x}+{y}")

        tk.Label(dlg, text="AUDIO OUTPUT", font=(self.font_family, 14, "bold"),
                 fg=C64_PALETTE["YELLOW"], bg=C64_PALETTE["BLACK"]).pack(pady=(12, 4))

        tk.Label(dlg, text="Seleziona destinazione audio:",
                 font=(self.font_family, 10), fg=C64_PALETTE["LIGHT_BLUE"],
                 bg=C64_PALETTE["BLACK"]).pack()

        list_frame = tk.Frame(dlg, bg=C64_PALETTE["BLACK"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=8)

        scrollbar = tk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(list_frame, font=(self.font_family, 10),
                             fg=C64_PALETTE["WHITE"], bg=C64_PALETTE["DARK_GREY"],
                             selectbackground=C64_PALETTE["LIGHT_BLUE"],
                             selectforeground=C64_PALETTE["BLACK"],
                             activestyle="none", bd=0,
                             yscrollcommand=scrollbar.set)
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)

        # Voce speciale per il default di sistema
        listbox.insert(tk.END, "  [Default di sistema]")
        current_sel = 0  # pre-seleziona default
        for pos, (dev_idx, dev_name) in enumerate(output_devices):
            listbox.insert(tk.END, f"  {dev_name}")
            if dev_idx == self.audio_engine.output_device:
                current_sel = pos + 1

        listbox.selection_set(current_sel)
        listbox.see(current_sel)

        def on_apply():
            sel = listbox.curselection()
            if not sel:
                dlg.destroy()
                return
            idx = sel[0]
            if idx == 0:
                self.audio_engine.output_device = None
                log_message("Audio output: default di sistema")
            else:
                dev_idx, dev_name = output_devices[idx - 1]
                self.audio_engine.output_device = dev_idx
                log_message(f"Audio output: {dev_name} (device {dev_idx})")
            dlg.destroy()

        btn_frame_dlg = tk.Frame(dlg, bg=C64_PALETTE["BLACK"])
        btn_frame_dlg.pack(pady=8)
        tk.Button(btn_frame_dlg, text="OK", command=on_apply,
                  font=(self.font_family, 12, "bold"),
                  fg=C64_PALETTE["BLACK"], bg=C64_PALETTE["LIGHT_BLUE"],
                  activebackground=C64_PALETTE["CYAN"], relief="raised", bd=3,
                  padx=20, pady=4).pack(side="left", padx=6)
        tk.Button(btn_frame_dlg, text="CANCEL", command=dlg.destroy,
                  font=(self.font_family, 12, "bold"),
                  fg=C64_PALETTE["BLACK"], bg=C64_PALETTE["LIGHT_BLUE"],
                  activebackground=C64_PALETTE["CYAN"], relief="raised", bd=3,
                  padx=20, pady=4).pack(side="left", padx=6)

    # ------------------------------------------------------------------

    def quit_all(self):
        self.now_playing.deactivate()
        _np_clear()
        self.audio_engine.stop()
        self.master.destroy()


def main():
    global DEBUG_MODE

    args = sys.argv[1:]

    if '-h' in args or '--help' in args:
        print(f"SIDPlayer C64 {VERSION}")
        print(f"\nPiattaforma: {sys.platform}")
        print("\nOpzioni:")
        print("  -d, --debug    Abilita messaggi di debug a video")
        print("  -h, --help     Mostra questo aiuto")
        return

    if '-d' in args or '--debug' in args:
        DEBUG_MODE = True

    # ------------------------------------------------------------------
    # Modalità silenziosa: su Windows nascondi la console, su Unix/macOS
    # staccati dal terminale (così il prompt torna subito disponibile).
    # ------------------------------------------------------------------
    if not DEBUG_MODE:
        if IS_WINDOWS:
            # Nasconde la finestra console se lanciato con python.exe
            # (con pythonw.exe non è necessario, ma non fa danni)
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(
                    ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except Exception:
                pass
        elif '--attached' not in args:
            # Unix/macOS: se c'è un terminale, ri-lancia staccato
            try:
                if os.isatty(sys.stdin.fileno()):
                    subprocess.Popen(
                        [sys.executable] + sys.argv + ['--attached'],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    sys.exit(0)
            except Exception:
                pass  # Se non riesce, continua normalmente

    if DEBUG_MODE:
        print("=" * 50)
        print(f"SIDPLAYER {VERSION} - DEBUG MODE")
        print(f"Piattaforma : {sys.platform}")
        print(f"FIFO        : {'sì' if HAS_FIFO else 'no (Windows → tempfile)'}")
        print(f"sounddevice : {'sì' if HAS_SOUNDDEVICE else 'no (riproduzione diretta)'}")
        print("=" * 50)

    log_message(f"=== SIDPlayer Avvio {VERSION} ({sys.platform}) ===")

    try:
        from PIL import Image, ImageTk
    except ImportError:
        log_message("ATTENZIONE: Pillow non installato - le immagini non saranno mostrate")

    config = Config()
    log_message(f"Config: {config.config_file}")
    config.ensure_directories()

    root = tk.Tk()
    app = SidTkPlayer(root, config=config)
    root.mainloop()


if __name__ == "__main__":
    main()
