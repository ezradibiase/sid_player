#!/usr/bin/env python3
"""
SIDPlayer C64-Style con supporto copertine C64 da IGDB e RAWG
Versione: v2.2 (SID Metadata Enhanced)
Autore: ezrad & IA
Anno: 2026
"""

import os
import random
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, filedialog
from pathlib import Path
from PIL import Image, ImageTk
import configparser

# Configura logging su file
LOG_FILE = "sidplayer_debug.log"

def log_message(msg):
    """Scrive un messaggio nel file di log"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, LOG_FILE)
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

# Nota: L'icona del dock viene gestita dall'app bundle macOS (Info.plist)
# Non è necessario impostarla via codice Python

# Prova a importare requests per le API
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("ATTENZIONE: 'requests' non installato. Il supporto API è disabilitato.")
    print("Installa con: pip install requests")
    log_message("ATTENZIONE: 'requests' non installato")

VERSION = "v2.2"
FONT_FAMILY_DEFAULT = "C64 Pro Mono"  # Nome del font se installato
FONT_FALLBACK = "Courier"  # Font di fallback se C64 Pro Mono non è presente
CONFIG_FILE = "sidplayer.cfg"

C64_PALETTE = {
    "EZ_LBLUE": "#8B8FF7", "EZ_BLUE": "#383BF0", "EZ_DBLUE": "#3134D2",
    "BLACK": "#000000", "WHITE": "#FFFFFF", "RED": "#880000", "CYAN": "#AAFFEE",
    "PURPLE": "#CC44CC", "GREEN": "#00CC55", "BLUE": "#0000AA", "YELLOW": "#EEEE77",
    "ORANGE": "#DD8855", "BROWN": "#664400", "PINK": "#FF7777", "DARK_GREY": "#333333",
    "GREY": "#777777", "LIGHT_GREEN": "#AAFF66", "LIGHT_BLUE": "#0088FF", "LIGHT_GREY": "#BBBBBB"
}


def get_available_font(preferred_font, fallback_font):
    """
    Verifica se il font preferito è disponibile nel sistema.
    Se non lo è, usa il font di fallback.
    """
    try:
        # Prova a creare un font con il nome preferito
        test_font = (preferred_font, 12)
        # Se tkinter non lancia eccezioni, il font è disponibile
        return preferred_font
    except:
        return fallback_font


class Config:
    """Gestisce la configurazione dell'applicazione"""

    DEFAULTS = {
        'paths': {
            'images_dir': '~/Pictures/SIDPlayer',
            'playlist_file': 'playlist.txt',
        },
        'api': {
            'rawg_api_key': '',
            'igdb_client_id': '',
            'igdb_access_token': '',
        },
        'player': {
            'sidplay_cmd': 'sidplayfp',
        },
        'window': {
            'width': '640',
            'height': '480',
            'resizable': 'false',
        }
    }

    def __init__(self, config_file=CONFIG_FILE):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # Se il percorso è relativo, cerca in queste posizioni (in ordine):
        # 1. Directory dell'utente (~/Library/Application Support/SIDPlayer/)
        # 2. Directory home (~)
        # 3. Directory dello script (per app bundle o sviluppo)
        if not os.path.isabs(self.config_file):
            # Percorsi preferiti per la configurazione utente
            user_config_dir = os.path.expanduser("~/Library/Application Support/SIDPlayer")
            user_config_path = os.path.join(user_config_dir, self.config_file)
            home_config_path = os.path.expanduser(f"~/{self.config_file}")
            
            script_dir = os.path.dirname(os.path.abspath(__file__))
            script_config_path = os.path.join(script_dir, self.config_file)
            
            # Cerca il file di configurazione in ordine di priorità
            if os.path.exists(user_config_path):
                self.config_file = user_config_path
                log_message(f"Config trovata in: {self.config_file} (user)")
            elif os.path.exists(home_config_path):
                self.config_file = home_config_path
                log_message(f"Config trovata in: {self.config_file} (home)")
            else:
                self.config_file = script_config_path
                log_message(f"Config trovata in: {self.config_file} (script)")
        
        self._load_config()
        # Determina il font disponibile nel sistema
        self._font_family = get_available_font(FONT_FAMILY_DEFAULT, FONT_FALLBACK)
        if self._font_family == FONT_FALLBACK:
            log_message(f"Font '{FONT_FAMILY_DEFAULT}' non trovato. Uso '{FONT_FALLBACK}'")
        else:
            log_message(f"Font '{FONT_FAMILY_DEFAULT}' disponibile")

    def _load_config(self):
        """Carica la configurazione dal file o usa i default"""
        # Imposta i default
        for section, options in self.DEFAULTS.items():
            self.config.setdefault(section, {})
            for key, value in options.items():
                if key not in self.config[section]:
                    self.config[section][key] = value
        
        # Tenta di caricare il file di configurazione
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                print(f"✓ Configurazione caricata da: {self.config_file}")
            except Exception as e:
                print(f"⚠ Errore lettura config: {e}. Uso i default.")
        else:
            print(f"ℹ File {self.config_file} non trovato. Uso i default.")
            print(f"  Copia 'sidplayer.cfg.example' in '{self.config_file}' per personalizzare.")
    
    def get(self, section, option, fallback=None):
        """Ottiene un valore dalla configurazione"""
        return self.config.get(section, option, fallback=fallback)
    
    def getboolean(self, section, option, fallback=False):
        """Ottiene un valore booleano dalla configurazione"""
        return self.config.getboolean(section, option, fallback=fallback)
    
    def getint(self, section, option, fallback=0):
        """Ottiene un valore intero dalla configurazione"""
        return self.config.getint(section, option, fallback=fallback)
    
    @property
    def images_dir(self):
        """Ottiene la directory delle immagini espansa"""
        path = self.get('paths', 'images_dir')
        return os.path.expanduser(os.path.expandvars(path))
    
    @property
    def playlist_file(self):
        """Ottiene il percorso del file playlist"""
        path = self.get('paths', 'playlist_file')
        # Se il percorso è relativo, lo cerca nella directory dello script
        if not os.path.isabs(path):
            script_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(script_dir, path)
        return os.path.expanduser(os.path.expandvars(path))
    
    @property
    def rawg_api_key(self):
        """Ottiene l'API key di RAWG"""
        return self.get('api', 'rawg_api_key')
    
    @property
    def igdb_client_id(self):
        """Ottiene il Client ID di IGDB"""
        return self.get('api', 'igdb_client_id')
    
    @property
    def igdb_access_token(self):
        """Ottiene l'Access Token di IGDB"""
        return self.get('api', 'igdb_access_token')
    
    @property
    def sidplay_cmd(self):
        """Ottiene il comando per riprodurre i SID"""
        return self.get('player', 'sidplay_cmd')

    @property
    def font_family(self):
        """Ottiene la famiglia del font (rilevata dal sistema)"""
        return self._font_family
    
    @property
    def window_width(self):
        """Ottiene la larghezza della finestra"""
        return self.getint('window', 'width', 640)
    
    @property
    def window_height(self):
        """Ottiene l'altezza della finestra"""
        return self.getint('window', 'height', 480)
    
    @property
    def window_resizable(self):
        """Ottiene se la finestra è ridimensionabile"""
        return self.getboolean('window', 'resizable', False)
    
    def ensure_directories(self):
        """Crea le directory necessarie se non esistono"""
        images_dir = self.images_dir
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
            print(f"✓ Creata directory immagini: {images_dir}")
        return images_dir

C64_PALETTE = {
    "EZ_LBLUE": "#8B8FF7", "EZ_BLUE": "#383BF0", "EZ_DBLUE": "#3134D2",
    "BLACK": "#000000", "WHITE": "#FFFFFF", "RED": "#880000", "CYAN": "#AAFFEE",
    "PURPLE": "#CC44CC", "GREEN": "#00CC55", "BLUE": "#0000AA", "YELLOW": "#EEEE77",
    "ORANGE": "#DD8855", "BROWN": "#664400", "PINK": "#FF7777", "DARK_GREY": "#333333",
    "GREY": "#777777", "LIGHT_GREEN": "#AAFF66", "LIGHT_BLUE": "#0088FF", "LIGHT_GREY": "#BBBBBB"
}

class RAWGGameImages:
    def __init__(self, api_key, images_dir):
        """Inizializza il client RAWG.io con filtro per Commodore 64"""
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"
        self.images_dir = Path(images_dir)
        self.c64_platform_id = 15  # ID specifico per Commodore 64 su RAWG
        
    def clean_game_name(self, game_name):
        """Pulisce il nome del gioco per la ricerca su RAWG"""
        import re
        
        # Se viene passato un nome file, rimuovi estensione e path
        if game_name.lower().endswith('.sid'):
            game_name = game_name[:-4]
        
        # Sostituisci underscore con spazi
        game_name = game_name.replace('_', ' ')
        
        # Rimuovi pattern comuni nei titoli SID
        patterns = [
            r'\s*\(\d{4}\)\s*$',        # (1984)
            r'\s*\d{4}\s*$',            # 1984
            r'\s*\[.*?\]\s*$',          # [V1]
            r'\s*\(.*?version.*?\)\s*$', # (demo version)
            r'\s*(remix|version|demo|beta|alpha|unreleased)\s*$',
            r'\s*\d{2}\s*$',            # 01, 02
            r'\s*(c64|commodore|sid)\s*$',  # game c64
        ]
        
        for pattern in patterns:
            game_name = re.sub(pattern, '', game_name, flags=re.IGNORECASE)
        
        # Rimuovi spazi multipli e spazi iniziali/finali
        game_name = re.sub(r'\s+', ' ', game_name).strip()
        
        return game_name
    
    def search_game_c64_only(self, game_name):
        """Cerca UNICAMENTE giochi per Commodore 64 su RAWG.io"""
        if not HAS_REQUESTS:
            return None
            
        endpoint = f"{self.base_url}/games"
        params = {
            'key': self.api_key,
            'search': game_name,
            'platforms': self.c64_platform_id,  # FILTRO CRITICO: solo C64
            'page_size': 5,
            'ordering': '-rating'
        }
        
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data['results']:
                # Filtra ulteriormente: solo giochi che hanno C64 come piattaforma
                for game in data['results']:
                    platform_ids = [p['platform']['id'] for p in game['platforms']]
                    if self.c64_platform_id in platform_ids:
                        if game.get('background_image'):
                            return game
                return data['results'][0]
            return None
        except Exception as e:
            print(f"Errore ricerca RAWG per '{game_name}': {e}")
            return None
    
    def download_game_image(self, game_name, sid_filename=None):
        """
        Scarica l'immagine del gioco corrispondente al titolo.
        Ritorna il percorso del file scaricato o None.
        """
        if not HAS_REQUESTS:
            return None
            
        game_name_clean = self.clean_game_name(game_name)
        print(f"Ricerca su RAWG (solo C64) per: '{game_name_clean}' (da: '{game_name}')")
        game = self.search_game_c64_only(game_name_clean)
        
        if not game:
            print(f"Gioco C64 non trovato su RAWG: {game_name_clean}")
            return None
        
        # VERIFICA: controlla che sia veramente per C64
        platform_names = [p['platform']['name'] for p in game['platforms']]
        c64_platforms = ['Commodore / Amiga', 'Commodore 64', 'C64']
        has_c64 = any(c64 in str(p) for c64 in c64_platforms for p in platform_names)
        
        if not has_c64:
            print(f"AVVISO: Gioco {game['name']} non è per C64. Piattaforme: {platform_names}")
            return None
        
        # Prendi l'URL dell'immagine di sfondo
        image_url = None
        if game.get('background_image'):
            image_url = game['background_image']
            print(f"Trovata immagine per {game['name']} (C64 confermato)")
        
        if not image_url:
            print(f"Nessuna immagine disponibile per {game['name']}")
            return None
        
        # Crea il nome del file di output basato sul nome del gioco (sicuro per filesystem)
        safe_game_name = "".join(c for c in game['name'] if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_game_name:
            # Fallback al nome del file SID se necessario
            if sid_filename:
                safe_game_name = sid_filename.replace('.sid', '').replace('.SID', '')
            else:
                safe_game_name = game_name_clean
        
        output_filename = f"{safe_game_name}.jpg"
        output_path = self.images_dir / output_filename
        
        # Se il file esiste già, restituisci il percorso
        if output_path.exists():
            print(f"Immagine già presente in cache: {output_path}")
            return str(output_path)
        
        # Scarica l'immagine
        try:
            print(f"Download immagine da: {image_url[:80]}...")
            response = requests.get(image_url, timeout=15)
            response.raise_for_status()
            
            # Assicurati che la directory esista
            self.images_dir.mkdir(exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            print(f"Immagine C64 scaricata e salvata in: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"Errore download immagine per {game['name']}: {e}")
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
        self.c64_platform_id = 15  # CORRETTO: ID 15 per Commodore 64
        
    def clean_game_name(self, game_name):
        """Pulisce il nome del gioco per la ricerca su IGDB"""
        import re
        
        # Se viene passato un nome file, rimuovi estensione e path
        if game_name.lower().endswith('.sid'):
            game_name = game_name[:-4]
        
        # Sostituisci underscore con spazi
        game_name = game_name.replace('_', ' ')
        
        # Rimuove annotazioni comuni nei titoli SID
        patterns = [
            r'\s*\(\d{4}\)\s*$',        # (1984)
            r'\s*\d{4}\s*$',            # 1984
            r'\s*\[.*?\]\s*$',          # [V1]
            r'\s*\(.*?version.*?\)\s*$', # (demo version)
            r'\s*(remix|version|demo|beta|alpha|unreleased)\s*$',
            r'\s*\d{2}\s*$',            # 01, 02
            r'\s*(c64|commodore|sid)\s*$',  # game c64
            r'\s*-\s*.*$',              # - Remix, - Theme, etc.
        ]
        
        for pattern in patterns:
            game_name = re.sub(pattern, '', game_name, flags=re.IGNORECASE)
        
        # Rimuovi spazi multipli e spazi iniziali/finali
        game_name = re.sub(r'\s+', ' ', game_name).strip()
        
        return game_name
    
    def search_game_c64_only(self, game_name):
        """Cerca giochi per nome su IGDB e filtra solo quelli per C64"""
        if not HAS_REQUESTS:
            return None
            
        endpoint = f"{self.base_url}/games"
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        # Query IGDB: cerca per nome e ottiene cover e piattaforme
        body = f"""
        fields name, cover.*, platforms.*;
        search "{game_name}";
        limit 10;
        """
        
        try:
            print(f"Invio richiesta a IGDB per: '{game_name}'")
            response = requests.post(endpoint, headers=headers, data=body, timeout=15)
            
            # Gestione errori
            if response.status_code == 401:
                print("ERRORE 401: Access Token IGDB non valido o scaduto!")
                return None
            elif response.status_code == 403:
                print("ERRORE 403: Client ID non autorizzato")
                return None
            elif response.status_code != 200:
                print(f"ERRORE IGDB {response.status_code}: {response.text}")
                return None
            
            response.raise_for_status()
            games = response.json()
            print(f"IGDB: trovati {len(games)} giochi totali")
            
            if games:
                # Filtra i giochi che hanno la piattaforma C64 (id 15)
                c64_games = []
                for game in games:
                    if 'platforms' in game:
                        # Controlla se c'è una piattaforma con id 15
                        platform_ids = []
                        for platform in game['platforms']:
                            if isinstance(platform, dict) and 'id' in platform:
                                platform_ids.append(platform['id'])
                            elif isinstance(platform, int):
                                platform_ids.append(platform)
                        
                        if self.c64_platform_id in platform_ids:
                            c64_games.append(game)
                
                print(f"IGDB: {len(c64_games)} giochi per C64")
                
                # Preferisci giochi con copertina
                for game in c64_games:
                    if 'cover' in game:
                        print(f"✓ Trovata copertina C64 per: {game.get('name', 'N/A')}")
                        return game
                
                # Se nessuno ha copertina, restituisci il primo gioco C64
                if c64_games:
                    print(f"⚠️  Nessuna copertina, uso primo gioco C64: {c64_games[0].get('name', 'N/A')}")
                    return c64_games[0]
                else:
                    print("Nessun gioco C64 trovato")
                    return None
            else:
                print(f"IGDB: nessun gioco trovato per '{game_name}'")
                return None
                
        except requests.exceptions.Timeout:
            print(f"Timeout nella richiesta IGDB per '{game_name}'")
            return None
        except Exception as e:
            print(f"Errore ricerca IGDB per '{game_name}': {type(e).__name__} - {e}")
            return None
    
    def get_cover_url(self, cover_data):
        """Costruisce l'URL della copertina da IGDB"""
        if not cover_data:
            return None
            
        if isinstance(cover_data, int):
            image_id = cover_data
        elif isinstance(cover_data, dict) and 'image_id' in cover_data:
            image_id = cover_data['image_id']
        else:
            return None
        
        # Formato cover_big per copertine di buona qualità
        return f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
    
    def download_game_image(self, game_name, sid_filename=None):
        """
        Scarica la COPERTINA del gioco C64 da IGDB.
        Ritorna il percorso del file scaricato o None.
        """
        if not HAS_REQUESTS:
            return None
            
        game_name_clean = self.clean_game_name(game_name)
        print(f"Ricerca copertina su IGDB (solo C64) per: '{game_name_clean}' (da: '{game_name}')")
        game = self.search_game_c64_only(game_name_clean)
        
        if not game:
            print(f"Gioco C64 non trovato su IGDB: {game_name_clean}")
            return None
        
        if 'cover' not in game:
            print(f"Gioco {game.get('name', 'N/A')} non ha copertina su IGDB")
            return None
        
        # Ottieni URL della copertina
        cover_url = self.get_cover_url(game['cover'])
        if not cover_url:
            print(f"Impossibile ottenere URL copertina per {game.get('name', 'N/A')}")
            return None
        
        print(f"Trovata copertina C64 per: {game.get('name', 'N/A')}")
        
        # Crea il nome del file di output basato sul nome del gioco
        safe_game_name = "".join(c for c in game.get('name', game_name_clean) 
                                if c.isalnum() or c in (' ', '-', '_')).rstrip()
        output_filename = f"{safe_game_name}_COVER.jpg"
        output_path = self.images_dir / output_filename
        
        # Se il file esiste già, restituisci il percorso
        if output_path.exists():
            print(f"Copertina già presente in cache: {output_path}")
            return str(output_path)
        
        # Scarica la copertina
        try:
            print(f"Download copertina da: {cover_url}")
            response = requests.get(cover_url, timeout=15)
            response.raise_for_status()
            
            # Assicurati che la directory esista
            self.images_dir.mkdir(exist_ok=True)
            
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
            print(f"Copertina C64 scaricata e salvata in: {output_path}")
            return str(output_path)
        except Exception as e:
            print(f"Errore download copertina: {e}")
            if output_path.exists():
                output_path.unlink()
            return None

class SidTkPlayer:
    def __init__(self, master, config=None):
        self.master = master
        
        # Carica la configurazione
        self.config = config if config else Config()
        
        # Imposta le proprietà dalla configurazione
        self.images_dir = self.config.images_dir
        self.playlist_file = self.config.playlist_file
        self.sidplay_cmd = self.config.sidplay_cmd
        self.font_family = self.config.font_family
        
        # Imposta la finestra
        self.master.title(f"SIDPLAYER C64 {VERSION}")
        self.master.configure(bg=C64_PALETTE["BLACK"])
        self.master.geometry(f"{self.config.window_width}x{self.config.window_height}")
        self.master.resizable(self.config.window_resizable, self.config.window_resizable)

        # API RAWG
        self.rawg_api_key = self.config.rawg_api_key
        self.rawg_fetcher = None
        if self.rawg_api_key and HAS_REQUESTS:
            self.rawg_fetcher = RAWGGameImages(self.rawg_api_key, self.images_dir)
            print("Supporto RAWG.io attivato (solo C64) - basato su metadata SID")

        # API IGDB (raccomandato per copertine)
        self.igdb_client_id = self.config.igdb_client_id
        self.igdb_access_token = self.config.igdb_access_token
        self.igdb_fetcher = None
        if self.igdb_client_id and self.igdb_access_token and HAS_REQUESTS:
            self.igdb_fetcher = IGDBGameImages(self.igdb_client_id, self.igdb_access_token, self.images_dir)
            print("Supporto IGDB attivato (copertine C64) - basato su metadata SID")

        if not self.rawg_fetcher and not self.igdb_fetcher:
            print("ℹ Nessun servizio API attivato. Solo immagini locali.")
        
        print(f"📁 Directory immagini: {self.images_dir}")
        print("Priorità ricerca immagini: IGDB → RAWG → Locale (tramite metadata SID)")

        self.canvas = tk.Canvas(master, width=self.config.window_width, height=self.config.window_height, bg=C64_PALETTE["BLACK"], highlightthickness=0)
        self.canvas.pack()
        for i in range(0, self.config.window_height, 4):
            self.canvas.create_line(0, i, self.config.window_width, i, fill="#111111", width=1)

        # Header
        header_frame = tk.Frame(self.canvas, bg=C64_PALETTE["BLUE"], height=32)
        header_frame.place(x=0, y=0, width=self.config.window_width)
        tk.Label(header_frame, text="SIDPLAYER", font=(self.font_family, 18, "bold"),
                fg=C64_PALETTE["WHITE"], bg=C64_PALETTE["BLUE"]).place(x=20, y=6)

        # Schermo centrale
        self.screen_frame = tk.Frame(self.canvas, bg=C64_PALETTE["DARK_GREY"], relief="raised", bd=2)
        self.screen_frame.place(x=24, y=48, width=592, height=100)

        self.label_title = tk.Label(self.screen_frame, text="LOAD & PLAY",
            font=(self.font_family, 18, "bold"), fg=C64_PALETTE["LIGHT_GREEN"],
            bg=C64_PALETTE["DARK_GREY"], wraplength=560, justify="center")
        self.label_title.place(x=16, y=10)

        self.label_subtitle = tk.Label(self.screen_frame, text="Click LOAD then PLAY",
            font=(self.font_family, 10), fg=C64_PALETTE["CYAN"],
            bg=C64_PALETTE["DARK_GREY"], wraplength=560, justify="center")
        self.label_subtitle.place(x=16, y=50)

        # Frame per l'immagine del videogioco
        self.image_frame = tk.Frame(self.canvas, bg=C64_PALETTE["BLACK"], relief="flat", bd=0)
        self.image_frame.place(x=24, y=160, width=592, height=200)

        # Frame interno per l'immagine
        self.image_container = tk.Frame(self.image_frame, bg=C64_PALETTE["BLACK"])
        self.image_container.pack(expand=True, fill='both')

        self.image_label = tk.Label(self.image_container, bg=C64_PALETTE["BLACK"])
        self.image_label.pack(expand=True)

        # Label per la fonte dell'immagine
        self.image_source_label = tk.Label(self.image_frame,
                                          text="",
                                          font=(self.font_family, 8),
                                          fg=C64_PALETTE["GREY"],
                                          bg=C64_PALETTE["BLACK"])
        self.image_source_label.pack(side='bottom', pady=(0, 5))

        # Status bar (spostata più in basso)
        self.status_frame = tk.Frame(self.canvas, bg=C64_PALETTE["EZ_DBLUE"], height=32)
        self.status_frame.place(x=0, y=448, width=self.config.window_width)
        self.status_label = tk.Label(self.status_frame, text="READY. TO PLAY.",
            font=(self.font_family, 14, "bold"), fg=C64_PALETTE["EZ_LBLUE"], bg=C64_PALETTE["EZ_DBLUE"])
        self.status_label.place(x=10, y=6)

        # Pulsanti (spostati più in basso, sopra la status bar)
        btn_frame = tk.Frame(self.canvas, bg=C64_PALETTE["BLACK"])
        btn_frame.place(x=24, y=416, width=592, height=32)

        self.buttons = []
        button_config = [
            ("LOAD", self.load_files_dialog),
            ("PLAY", self.start_playlist),
            ("NEXT", self.skip_track),
            ("STOP", self.stop_playlist),
            ("ABOUT", self.show_about),
            ("QUIT", self.quit_all)
        ]

        for i, (text, cmd) in enumerate(button_config):
            btn = tk.Button(btn_frame, text=text, command=cmd, font=(self.font_family, 14, "bold"),
                fg=C64_PALETTE["BLACK"], bg=C64_PALETTE["LIGHT_BLUE"],
                activebackground=C64_PALETTE["CYAN"], activeforeground=C64_PALETTE["WHITE"],
                relief="raised", bd=4, padx=5, pady=6, width=10, anchor="center")
            btn.grid(row=0, column=i, sticky="nsew", padx=2)
            self.buttons.append(btn)

        for i in range(len(button_config)):
            btn_frame.columnconfigure(i, weight=1)

        # Stato
        self.tracks = []
        self.current_index = -1
        self.current_process = None
        self.playing = False
        self.total_tracks = 0
        self.current_image = None

        # Verifica se la directory images esiste
        if not os.path.exists(self.images_dir):
            print(f"AVVISO: Directory immagini non trovata: {self.images_dir}")
            print("Creo la directory 'images'...")
            os.makedirs(self.images_dir, exist_ok=True)

        # Carica automaticamente la playlist se esiste
        self.load_playlist_file()
        self.update_status()

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
            print(f"Error reading SID title from {sid_path}: {e}")
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
            print(f"Error reading SID author from {sid_path}: {e}")
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
            print(f"Error reading SID released from {sid_path}: {e}")
            return ""
    
    def blink_title(self):
        current_fg = self.label_title.cget("fg")
        self.label_title.config(fg=C64_PALETTE["YELLOW"])
        self.master.after(200, lambda: self.label_title.config(fg=current_fg))
    
    def update_status(self):
        if self.playing and self.total_tracks > 0:
            track_num = f"{self.current_index+1}/{self.total_tracks}"
            self.status_label.config(text=f"PLAYING {track_num}")
        elif self.total_tracks > 0:
            self.status_label.config(text=f"{self.total_tracks} files loaded - READY")
        else:
            self.status_label.config(text="READY - CLICK LOAD THEN PLAY")
    
    def load_files_dialog(self):
        """Mostra un menu per scegliere cosa caricare: file SID o playlist"""
        # Crea un dialog per chiedere cosa caricare
        dialog = tk.Toplevel(self.master)
        dialog.title("LOAD")
        dialog.configure(bg=C64_PALETTE["BLACK"])
        dialog.geometry("350x180")
        dialog.resizable(False, False)
        dialog.transient(self.master)
        dialog.grab_set()
        
        # Titolo
        title_label = tk.Label(dialog, text="Cosa vuoi caricare?",
                              font=(self.font_family, 14, "bold"),
                              fg=C64_PALETTE["LIGHT_GREEN"],
                              bg=C64_PALETTE["BLACK"])
        title_label.pack(pady=(20, 15))
        
        # Frame per i bottoni
        btn_frame = tk.Frame(dialog, bg=C64_PALETTE["BLACK"])
        btn_frame.pack(pady=(0, 20))
        
        def on_sid_files():
            dialog.destroy()
            self._load_sid_files()
        
        def on_playlist():
            dialog.destroy()
            self._load_playlist_dialog()
        
        # Pulsante SID Files
        btn_sid = tk.Button(btn_frame, text="SID FILES",
                           command=on_sid_files,
                           font=(self.font_family, 12, "bold"),
                           fg=C64_PALETTE["BLACK"],
                           bg=C64_PALETTE["LIGHT_BLUE"],
                           activebackground=C64_PALETTE["CYAN"],
                           activeforeground=C64_PALETTE["WHITE"],
                           relief="raised", bd=4, padx=15, pady=5)
        btn_sid.pack(side=tk.LEFT, padx=10)
        
        # Pulsante PLAYLIST
        btn_playlist = tk.Button(btn_frame, text="PLAYLIST",
                                command=on_playlist,
                                font=(self.font_family, 12, "bold"),
                                fg=C64_PALETTE["BLACK"],
                                bg=C64_PALETTE["LIGHT_GREEN"],
                                activebackground=C64_PALETTE["CYAN"],
                                activeforeground=C64_PALETTE["WHITE"],
                                relief="raised", bd=4, padx=15, pady=5)
        btn_playlist.pack(side=tk.LEFT, padx=10)
        
        # Centra il dialog
        dialog.update_idletasks()
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (350 // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (180 // 2)
        dialog.geometry(f"350x180+{x}+{y}")
    
    def _load_sid_files(self):
        """Carica file SID selezionati dall'utente"""
        files = filedialog.askopenfilenames(
            title="Select SID files",
            filetypes=[("SID files", "*.sid"), ("All files", "*.*")]
        )
        if files:
            self.tracks = list(files)
            self.track_subsongs = {}  # Reset subsong map
            for i in range(len(files)):
                self.track_subsongs[i] = 1  # Default subsong 1 per tutti
            self.total_tracks = len(self.tracks)
            self.label_subtitle.config(text=f"{self.total_tracks} files loaded - Click PLAY")
            self.blink_title()
            self.update_status()
            log_message(f"Caricati {self.total_tracks} file SID manualmente")
    
    def _load_playlist_dialog(self):
        """Carica un file playlist selezionato dall'utente"""
        file_path = filedialog.askopenfilename(
            title="Select Playlist file",
            filetypes=[
                ("Playlist files", "*.txt *.cfg *.lst *.m3u *.pls"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            # Salva il percorso originale della playlist
            original_playlist = self.playlist_file
            
            # Imposta temporaneamente il percorso della playlist
            self.playlist_file = file_path
            
            # Carica la playlist
            if self.load_playlist_file():
                self.label_subtitle.config(text=f"{self.total_tracks} files from playlist - Click PLAY")
                self.blink_title()
                self.update_status()
                log_message(f"Playlist caricata da: {file_path}")
            else:
                messagebox.showerror("Error", "Failed to load playlist")
            
            # Ripristina il percorso originale della playlist
            self.playlist_file = original_playlist
    
    def load_playlist_file(self):
        """
        Carica il file playlist se esiste.
        Supporta qualsiasi estensione: .txt, .cfg, .lst, .m3u, .pls, ecc.
        Formato: /percorso/file.sid:traccia
        """
        playlist_path = self.playlist_file
        log_message(f"Cerco playlist: {playlist_path}")
        print(f"📋 Cerco playlist: {playlist_path}")

        if not os.path.exists(playlist_path):
            log_message(f"Playlist non trovata")
            print(f"  ⚠ Playlist non trovata")
            return False

        try:
            with open(playlist_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception as e:
            log_message(f"Errore lettura playlist: {e}")
            print(f"  ⚠ Errore lettura playlist: {e}")
            return False

        if not lines:
            log_message(f"Playlist vuota")
            print(f"  ⚠ Playlist vuota")
            return False

        # Espandi le variabili d'ambiente e i percorsi ~
        expanded = [os.path.expanduser(os.path.expandvars(line)) for line in lines]
        
        # Mischia la playlist (come in sid_play4.py)
        random.shuffle(expanded)
        
        # Parsa ogni riga per estrarre percorso e numero di traccia
        # Formato: /percorso/file.sid:traccia
        self.tracks = []
        self.track_subsongs = {}  # Mappa indice -> subsong
        
        for i, entry in enumerate(expanded):
            if ':' in entry:
                # Separa percorso e numero di traccia
                parts = entry.rsplit(':', 1)
                file_path = parts[0]
                try:
                    subsong = int(parts[1])
                except ValueError:
                    subsong = 1  # Default a 1 se non è un numero
            else:
                file_path = entry
                subsong = 1  # Default a 1 se non specificato
            
            # Aggiungi solo se il file esiste
            if os.path.exists(file_path):
                self.tracks.append(file_path)
                self.track_subsongs[len(self.tracks) - 1] = subsong
        
        self.total_tracks = len(self.tracks)
        
        log_message(f"Caricate {self.total_tracks} tracce dalla playlist")
        print(f"  ✓ Caricate {self.total_tracks} tracce dalla playlist (randomizzate)")
        return bool(self.tracks)
    
    def find_game_image(self, sid_path, sid_title):
        """
        Cerca un'immagine per il gioco in base al TITOLO SID (non nome file).
        Priorità: 1. IGDB (copertine), 2. RAWG (filtrato C64), 3. Locale
        Ritorna (percorso_immagine, fonte)
        """
        file_name = os.path.basename(sid_path)
        
        # Crea un nome sicuro per il file dal titolo SID
        safe_title = "".join(c for c in sid_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        if not safe_title:
            safe_title = file_name.replace('.sid', '').replace('.SID', '')
        
        # Cerca nella directory images locale
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir, exist_ok=True)
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        # 1. Cerca in locale per titolo (safe_title)
        for ext in image_extensions:
            # Cerca per titolo
            image_path = os.path.join(self.images_dir, safe_title + ext)
            if os.path.exists(image_path):
                print(f"Immagine trovata localmente per titolo '{sid_title}': {image_path}")
                return image_path, "Local file (by SID title)"
            
            # Cerca anche varianti con _COVER
            image_path = os.path.join(self.images_dir, safe_title + '_COVER' + ext)
            if os.path.exists(image_path):
                print(f"Copertina trovata localmente per titolo '{sid_title}': {image_path}")
                return image_path, "Local file (cover by SID title)"
        
        # 2. Cerca su IGDB per copertine usando il TITOLO SID
        if self.igdb_fetcher:
            print(f"Provo IGDB per copertina C64 con titolo SID: '{sid_title}'")
            downloaded_path = self.igdb_fetcher.download_game_image(sid_title, file_name)
            if downloaded_path:
                return downloaded_path, "IGDB (Cover C64 by SID title)"
        
        # 3. Cerca su RAWG filtrato per C64 usando il TITOLO SID
        if self.rawg_fetcher:
            print(f"Provo RAWG filtrato per C64 con titolo SID: '{sid_title}'")
            downloaded_path = self.rawg_fetcher.download_game_image(sid_title, file_name)
            if downloaded_path:
                return downloaded_path, "RAWG.io (C64 filtered by SID title)"
        
        print(f"Nessuna immagine trovata per il titolo SID: '{sid_title}'")
        return None, None
    
    def load_and_display_image(self, image_path, source):
        """Carica e mostra l'immagine ridimensionata con la fonte"""
        try:
            # Pulisci l'immagine precedente
            self.image_label.config(image='', text="")
            self.image_source_label.config(text="")
            if self.current_image:
                self.current_image = None
            
            # Carica l'immagine
            img = Image.open(image_path)
            
            # Ridimensiona mantenendo le proporzioni
            max_width = 580
            max_height = 170
            
            width_ratio = max_width / img.width
            height_ratio = max_height / img.height
            ratio = min(width_ratio, height_ratio)
            
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # Ridimensiona l'immagine
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Converti per Tkinter
            self.current_image = ImageTk.PhotoImage(img)
            self.image_label.config(image=self.current_image)
            
            # Mostra la fonte dell'immagine
            if source:
                self.image_source_label.config(text=f"Image source: {source}")
            
        except Exception as e:
            # Se c'è un errore, mostra un messaggio di fallback
            self.image_label.config(text=f"[Error loading image]\n{os.path.basename(image_path)}",
                                  font=(self.font_family, 8),
                                  fg=C64_PALETTE["RED"],
                                  bg=C64_PALETTE["BLACK"])
            self.image_source_label.config(text="")
    
    def start_playlist(self):
        if self.playing:
            return
        
        if not self.tracks:
            if self.load_playlist_file():
                self.label_subtitle.config(text=f"{self.total_tracks} files from playlist.txt")
            else:
                self.label_subtitle.config(text="No files found! Click LOAD first", fg=C64_PALETTE["RED"])
                return
        
        if not self.tracks:
            return
        
        self.playing = True
        self.buttons[0].config(state=tk.DISABLED)
        self.buttons[1].config(state=tk.DISABLED)
        self.buttons[2].config(state=tk.NORMAL)
        self.buttons[3].config(state=tk.NORMAL)
        self.play_next_track()
    
    def stop_playlist(self):
        if not self.playing:
            return
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
            self.current_process = None
        self.playing = False
        self.current_index = -1
        self.label_title.config(text="STOPPED", fg=C64_PALETTE["RED"])
        self.label_subtitle.config(text="Ready to load new files")
        # Pulisci l'immagine
        self.image_label.config(image='', text="")
        self.image_source_label.config(text="")
        self.buttons[0].config(state=tk.NORMAL)
        self.buttons[1].config(state=tk.NORMAL)
        self.buttons[2].config(state=tk.DISABLED)
        self.buttons[3].config(state=tk.NORMAL)
        self.update_status()
    
    def play_next_track(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
            self.current_process = None

        self.current_index += 1
        if self.current_index >= len(self.tracks):
            self.label_title.config(text="END OF PLAYLIST", fg=C64_PALETTE["CYAN"])
            self.label_subtitle.config(text="All tracks completed")
            self.image_label.config(image='', text="")
            self.image_source_label.config(text="")
            self.playing = False
            self.buttons[0].config(state=tk.NORMAL)
            self.buttons[1].config(state=tk.NORMAL)
            self.buttons[2].config(state=tk.DISABLED)
            self.buttons[3].config(state=tk.NORMAL)
            self.update_status()
            return

        track_path = self.tracks[self.current_index]
        if not os.path.exists(track_path):
            self.master.after(2000, self.play_next_track)
            return

        # Leggi titolo, autore e copyright dal file SID
        title = self.get_sid_title(track_path)
        author = self.get_sid_author(track_path)
        released = self.get_sid_released(track_path)
        
        self.label_title.config(text=title, fg=C64_PALETTE["LIGHT_GREEN"])
        
        # Mostra autore e copyright (se disponibile)
        if released:
            self.label_subtitle.config(text=f"by {author} - {released}", fg=C64_PALETTE["CYAN"])
        else:
            self.label_subtitle.config(text=f"by {author}", fg=C64_PALETTE["CYAN"])
            
        self.blink_title()
        self.update_status()

        # Cerca e mostra l'immagine del videogioco usando il TITOLO SID (non il nome del file)
        image_path, image_source = self.find_game_image(track_path, title)
        if image_path:
            self.load_and_display_image(image_path, image_source)
        else:
            # Mostra che non è stata trovata un'immagine per il titolo SID
            status_text = f"[No image found for SID title: {title}]"
            if self.igdb_fetcher or self.rawg_fetcher:
                status_text += f"\nC64 search enabled (by SID metadata)"
            self.image_label.config(text=status_text,
                                  font=(self.font_family, 8),
                                  fg=C64_PALETTE["GREY"],
                                  bg=C64_PALETTE["BLACK"])
            self.image_source_label.config(text="")

        try:
            # Ottieni il numero di subsong per questa traccia
            subsong = self.track_subsongs.get(self.current_index, 1)
            
            # Esegui sidplayfp con l'opzione -os<num> per specificare la traccia
            self.current_process = subprocess.Popen(
                [self.sidplay_cmd, f"-os{subsong}", track_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            log_message(f"Riproduzione: {track_path} (traccia {subsong})")
        except FileNotFoundError:
            messagebox.showerror("Error", f"{self.sidplay_cmd} not found in PATH")
            self.stop_playlist()
            return

        self.master.after(1000, self.check_track_done)
    
    def check_track_done(self):
        if self.current_process is None:
            return
        ret = self.current_process.poll()
        if ret is None:
            self.master.after(1000, self.check_track_done)
        else:
            self.current_process = None
            self.play_next_track()
    
    def skip_track(self):
        if not self.playing:
            return
        self.play_next_track()
    
    def show_about(self):
        """Mostra la finestra About con banner ASCII art"""
        about_window = tk.Toplevel(self.master)
        about_window.title("About SIDPLAYER")
        about_window.configure(bg=C64_PALETTE["BLACK"])
        about_window.geometry("520x600")  # Dimensione per banner + contenuti
        about_window.resizable(False, False)

        # Titolo
        title_label = tk.Label(about_window, text="SIDPLAYER C64",
                              font=(self.font_family, 24, "bold"),
                              fg=C64_PALETTE["LIGHT_GREEN"],
                              bg=C64_PALETTE["BLACK"])
        title_label.pack(pady=(15, 5))

        # Versione
        version_label = tk.Label(about_window, text=VERSION,
                               font=(self.font_family, 14),
                               fg=C64_PALETTE["CYAN"],
                               bg=C64_PALETTE["BLACK"])
        version_label.pack(pady=(0, 5))

        # Autore
        author_label = tk.Label(about_window, text="Author: ezrad & IA",
                               font=(self.font_family, 12),
                               fg=C64_PALETTE["WHITE"],
                               bg=C64_PALETTE["BLACK"])
        author_label.pack(pady=(0, 15))

        # Carica il banner ASCII art SOTTO all'autore
        banner_path = None
        banner_image = None
        
        # Cerca il banner in diverse posizioni
        possible_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "sidplayer_banner.png"),
            os.path.expanduser("~/Library/Application Support/SIDPlayer/sidplayer_banner.png"),
            "sidplayer_banner.png",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                banner_path = path
                break
        
        if banner_path:
            try:
                img = Image.open(banner_path)
                # Ridimensiona se necessario (max 480px larghezza)
                max_width = 480
                ratio = min(max_width / img.width, 1.0)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                banner_image = ImageTk.PhotoImage(img)
                
                banner_label = tk.Label(about_window, image=banner_image, bg=C64_PALETTE["BLACK"])
                banner_label.image = banner_image  # Mantieni riferimento
                banner_label.pack(pady=(5, 10))
            except Exception as e:
                log_message(f"Errore caricamento banner: {e}")

        # Anno
        year_label = tk.Label(about_window, text="2026",
                             font=(self.font_family, 12),
                             fg=C64_PALETTE["YELLOW"],
                             bg=C64_PALETTE["BLACK"])
        year_label.pack(pady=(5, 5))

        # Descrizione
        desc_label = tk.Label(about_window,
                             text="C64 SID Music Player\nwith C64 cover art support",
                             font=(self.font_family, 10),
                             fg=C64_PALETTE["LIGHT_GREY"],
                             bg=C64_PALETTE["BLACK"])
        desc_label.pack(pady=(5, 5))

        # Info metadata
        info_label = tk.Label(about_window,
                             text="Uses SID header metadata for image search",
                             font=(self.font_family, 8),
                             fg=C64_PALETTE["GREY"],
                             bg=C64_PALETTE["BLACK"])
        info_label.pack(pady=(5, 5))

        # Contatti
        contact_label = tk.Label(about_window,
                                text="github.com/ezradibiase",
                                font=(self.font_family, 9),
                                fg=C64_PALETTE["LIGHT_BLUE"],
                                bg=C64_PALETTE["BLACK"])
        contact_label.pack(pady=(10, 5))

        # Pulsante di chiusura
        close_btn = tk.Button(about_window, text="CLOSE",
                             command=about_window.destroy,
                             font=(self.font_family, 12, "bold"),
                             fg=C64_PALETTE["BLACK"],
                             bg=C64_PALETTE["LIGHT_BLUE"],
                             padx=20, pady=5, anchor="center")
        close_btn.pack(pady=(15, 0))

        # Centra la finestra
        about_window.transient(self.master)
        about_window.grab_set()
        about_window.focus_set()

        # Centra la finestra rispetto alla finestra principale
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (520 // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (600 // 2)
        about_window.geometry(f"520x600+{x}+{y}")
    
    def quit_all(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
        self.master.destroy()

def main():
    # Log avvio programma
    log_message("=== SIDPlayer Avvio ===")
    log_message(f"Versione: {VERSION}")
    
    # Verifica se PIL/Pillow è installato
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("ATTENZIONE: Pillow non è installato.")
        print("Le immagini dei videogiochi non potranno essere mostrate.")
        print("Installa con: pip install Pillow")
        log_message("ATTENZIONE: Pillow non installato")

        # Crea una versione senza supporto immagini
        global SidTkPlayer
        original_init = SidTkPlayer.__init__
        def patched_init(self, master):
            original_init(self, master)
            # Modifica l'interfaccia per mostrare messaggio invece di immagini
            self.image_label.config(text="[Install Pillow for game images]",
                                  font=(self.font_family, 10),
                                  fg=C64_PALETTE["RED"],
                                  bg=C64_PALETTE["BLACK"])

        SidTkPlayer.__init__ = patched_init

    # Carica la configurazione
    log_message("Caricamento configurazione...")
    config = Config()
    log_message(f"Config caricata da: {config.config_file}")

    # Crea le directory necessarie
    config.ensure_directories()

    root = tk.Tk()
    log_message("GUI Tk inizializzata")

    # Messaggi informativi
    if config.rawg_api_key:
        print(f"✓ API Key RAWG trovata - Ricerche basate su metadata SID")
    else:
        print("ℹ API Key RAWG non configurata. RAWG disabilitato.")

    if config.igdb_client_id and config.igdb_access_token:
        print(f"✓ Credenziali IGDB trovate - Copertine C64 abilitate!")
        print(f"  Ricerche basate su titolo SID dai metadati")
    else:
        print("ℹ Credenziali IGDB non configurate. Per copertine accurate:")
        print("  1. Vai su https://api-docs.igdb.com/#authentication")
        print("  2. Ottieni Client ID e Access Token")
        print("  3. Salva in sidplayer.cfg nella sezione [api]")

    print("\n=== IMPORTANTE ===")
    print("Questa versione (v2.2) utilizza i metadati SID per le ricerche:")
    print("- Titolo, Autore e Copyright letti dall'header SID")
    print("- Ricerche immagini basate sul titolo SID (non sul nome del file)")
    print("=================\n")

    app = SidTkPlayer(root, config=config)
    root.mainloop()

if __name__ == "__main__":
    main()
