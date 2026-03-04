#!/usr/bin/env python3
"""
SIDPlayer C64-Style con supporto copertine C64 da IGDB e RAWG
Versione: v2.1
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

# Prova a importare requests per le API
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("ATTENZIONE: 'requests' non installato. Il supporto API è disabilitato.")
    print("Installa con: pip install requests")

VERSION = "v2.1"
PLAYLIST_FILE = "playlist.txt"
SIDPLAY_CMD = "sidplayfp"
FONT_FAMILY = "C64 Pro Mono"

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
        
    def clean_game_name(self, sid_filename):
        """Pulisce il nome del file SID per la ricerca su RAWG"""
        name = sid_filename.replace('.sid', '').replace('.SID', '')
        name = name.replace('_', ' ')
        import re
        name = re.sub(r'\s*\(\d{4}\)\s*$', '', name)
        name = re.sub(r'\s*\d{4}\s*$', '', name)
        name = re.sub(r'\s*\d{2}\s*$', '', name)
        name = re.sub(r'\s*(remix|version|demo|beta|alpha)\s*$', '', name, flags=re.IGNORECASE)
        return name.strip()
    
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
    
    def download_game_image(self, sid_filename):
        """
        Scarica l'immagine del gioco corrispondente al file SID.
        Ritorna il percorso del file scaricato o None.
        """
        if not HAS_REQUESTS:
            return None
            
        game_name_clean = self.clean_game_name(sid_filename)
        print(f"Ricerca su RAWG (solo C64) per: {game_name_clean}")
        game = self.search_game_c64_only(game_name_clean)
        
        if not game:
            print(f"Gioco C64 non trovato su RAWG: {game_name_clean}")
            return None
        
        # VERIFICA: controlla che sia veramente per C64
        platform_names = [p['platform']['name'] for p in game['platforms']]
        c64_platforms = ['Commodore / Amiga', 'Commodore 64']
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
        
        # Crea il nome del file di output
        output_filename = sid_filename.replace('.sid', '.jpg').replace('.SID', '.jpg')
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
        
    def clean_game_name(self, sid_filename):
        """Pulisce il nome del file SID per la ricerca su IGDB"""
        name = sid_filename.replace('.sid', '').replace('.SID', '')
        name = name.replace('_', ' ')
        import re
        
        # Rimuove annotazioni comuni nei file SID
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
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
        
        return name.strip()
    
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
            print(f"Invio richiesta a IGDB per: {game_name}")
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
    
    def download_game_image(self, sid_filename):
        """
        Scarica la COPERTINA del gioco C64 da IGDB.
        Ritorna il percorso del file scaricato o None.
        """
        if not HAS_REQUESTS:
            return None
            
        game_name_clean = self.clean_game_name(sid_filename)
        print(f"Ricerca copertina su IGDB (solo C64) per: {game_name_clean}")
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
        
        # Crea il nome del file di output
        output_filename = sid_filename.replace('.sid', '_COVER.jpg').replace('.SID', '_COVER.jpg')
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
    def __init__(self, master, rawg_api_key=None, igdb_client_id=None, igdb_access_token=None):
        self.master = master
        self.master.title(f"SIDPLAYER C64 {VERSION}")
        self.master.configure(bg=C64_PALETTE["BLACK"])
        self.master.geometry("640x480")
        self.master.resizable(False, False)
        
        # Determina la directory dell'eseguibile Python
        self.executable_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Directory per le immagini
        self.images_dir = os.path.join(self.executable_dir, "images")
        
        # API RAWG
        self.rawg_api_key = rawg_api_key
        self.rawg_fetcher = None
        if rawg_api_key and HAS_REQUESTS:
            self.rawg_fetcher = RAWGGameImages(rawg_api_key, self.images_dir)
            print("Supporto RAWG.io attivato (solo C64)")
        
        # API IGDB (raccomandato per copertine)
        self.igdb_client_id = igdb_client_id
        self.igdb_access_token = igdb_access_token
        self.igdb_fetcher = None
        if igdb_client_id and igdb_access_token and HAS_REQUESTS:
            self.igdb_fetcher = IGDBGameImages(igdb_client_id, igdb_access_token, self.images_dir)
            print("Supporto IGDB attivato (copertine C64)")
        
        print("Priorità ricerca immagini: IGDB → RAWG → Locale")
        
        self.canvas = tk.Canvas(master, width=640, height=480, bg=C64_PALETTE["BLACK"], highlightthickness=0)
        self.canvas.pack()
        for i in range(0, 480, 4):
            self.canvas.create_line(0, i, 640, i, fill="#111111", width=1)
        
        # Header
        header_frame = tk.Frame(self.canvas, bg=C64_PALETTE["BLUE"], height=32)
        header_frame.place(x=0, y=0, width=640)
        tk.Label(header_frame, text="SIDPLAYER", font=(FONT_FAMILY, 18, "bold"),
                fg=C64_PALETTE["WHITE"], bg=C64_PALETTE["BLUE"]).place(x=20, y=6)
        
        # Schermo centrale
        self.screen_frame = tk.Frame(self.canvas, bg=C64_PALETTE["DARK_GREY"], relief="raised", bd=2)
        self.screen_frame.place(x=24, y=48, width=592, height=100)
        
        self.label_title = tk.Label(self.screen_frame, text="LOAD & PLAY",
            font=(FONT_FAMILY, 18, "bold"), fg=C64_PALETTE["LIGHT_GREEN"],
            bg=C64_PALETTE["DARK_GREY"], wraplength=560, justify="center")
        self.label_title.place(x=16, y=10)
        
        self.label_subtitle = tk.Label(self.screen_frame, text="Click LOAD then PLAY",
            font=(FONT_FAMILY, 10), fg=C64_PALETTE["CYAN"],
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
                                          font=(FONT_FAMILY, 8),
                                          fg=C64_PALETTE["GREY"],
                                          bg=C64_PALETTE["BLACK"])
        self.image_source_label.pack(side='bottom', pady=(0, 5))
        
        # Status bar
        self.status_frame = tk.Frame(self.canvas, bg=C64_PALETTE["EZ_DBLUE"], height=32)
        self.status_frame.place(x=0, y=416, width=640)
        self.status_label = tk.Label(self.status_frame, text="READY. TO PLAY.",
            font=(FONT_FAMILY, 14, "bold"), fg=C64_PALETTE["EZ_LBLUE"], bg=C64_PALETTE["EZ_DBLUE"])
        self.status_label.place(x=10, y=6)
        
        # Pulsanti
        btn_frame = tk.Frame(self.canvas, bg=C64_PALETTE["BLACK"])
        btn_frame.place(x=24, y=384, width=592, height=32)
        
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
            btn = tk.Button(btn_frame, text=text, command=cmd, font=(FONT_FAMILY, 14, "bold"),
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
        files = filedialog.askopenfilenames(
            title="Select SID files",
            filetypes=[("SID files", "*.sid"), ("All files", "*.*")]
        )
        if files:
            self.tracks = list(files)
            self.total_tracks = len(self.tracks)
            self.label_subtitle.config(text=f"{self.total_tracks} files loaded - Click PLAY")
            self.blink_title()
            self.update_status()
    
    def load_playlist_file(self):
        if not os.path.exists(PLAYLIST_FILE):
            return False
        try:
            with open(PLAYLIST_FILE, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except:
            return False
        if not lines:
            return False
        expanded = [os.path.expanduser(os.path.expandvars(line)) for line in lines]
        random.shuffle(expanded)
        self.tracks = [p for p in expanded if os.path.exists(p)]
        self.total_tracks = len(self.tracks)
        return bool(self.tracks)
    
    def find_game_image(self, sid_path):
        """
        Cerca un'immagine con lo stesso nome del file SID.
        Priorità: 1. IGDB (copertine), 2. RAWG (filtrato C64), 3. Locale
        Ritorna (percorso_immagine, fonte)
        """
        file_name = os.path.basename(sid_path)
        base_name = os.path.splitext(file_name)[0]
        
        # Cerca nella directory images locale
        if not os.path.exists(self.images_dir):
            os.makedirs(self.images_dir, exist_ok=True)
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        # 1. Cerca in locale
        for ext in image_extensions:
            image_path = os.path.join(self.images_dir, base_name + ext)
            if os.path.exists(image_path):
                return image_path, "Local file"
            
            # Cerca anche varianti con _COVER
            image_path = os.path.join(self.images_dir, base_name + '_COVER' + ext)
            if os.path.exists(image_path):
                return image_path, "Local file (cover)"
        
        # 2. Cerca su IGDB per copertine (se configurato)
        if self.igdb_fetcher:
            print(f"Provo IGDB per copertina C64: {file_name}")
            downloaded_path = self.igdb_fetcher.download_game_image(file_name)
            if downloaded_path:
                return downloaded_path, "IGDB (Cover C64)"
        
        # 3. Cerca su RAWG filtrato per C64 (se configurato)
        if self.rawg_fetcher:
            print(f"Provo RAWG filtrato per C64: {file_name}")
            downloaded_path = self.rawg_fetcher.download_game_image(file_name)
            if downloaded_path:
                return downloaded_path, "RAWG.io (C64 filtered)"
        
        print(f"Nessuna immagine trovata per {file_name}")
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
                                  font=(FONT_FAMILY, 8),
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

        # Leggi titolo e autore dal file SID
        title = self.get_sid_title(track_path)
        author = self.get_sid_author(track_path)
        
        self.label_title.config(text=title, fg=C64_PALETTE["LIGHT_GREEN"])
        self.label_subtitle.config(text=f"by {author}", fg=C64_PALETTE["CYAN"])
        self.blink_title()
        self.update_status()

        # Cerca e mostra l'immagine del videogioco
        image_path, image_source = self.find_game_image(track_path)
        if image_path:
            self.load_and_display_image(image_path, image_source)
        else:
            file_name = os.path.basename(track_path)
            if file_name.lower().endswith(".sid"):
                file_name = file_name[:-4]
            
            status_text = "[No cover image found]"
            if self.igdb_fetcher or self.rawg_fetcher:
                status_text += f"\nC64 search enabled"
            self.image_label.config(text=status_text, 
                                  font=(FONT_FAMILY, 8),
                                  fg=C64_PALETTE["GREY"],
                                  bg=C64_PALETTE["BLACK"])
            self.image_source_label.config(text="")

        try:
            self.current_process = subprocess.Popen(
                [SIDPLAY_CMD, "-os1", track_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except FileNotFoundError:
            messagebox.showerror("Error", f"{SIDPLAY_CMD} not found in PATH")
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
        """Mostra la finestra About"""
        about_window = tk.Toplevel(self.master)
        about_window.title("About SIDPLAYER")
        about_window.configure(bg=C64_PALETTE["BLACK"])
        about_window.geometry("400x300")
        about_window.resizable(False, False)
        
        # Titolo
        title_label = tk.Label(about_window, text="SIDPLAYER C64", 
                              font=(FONT_FAMILY, 24, "bold"),
                              fg=C64_PALETTE["LIGHT_GREEN"],
                              bg=C64_PALETTE["BLACK"])
        title_label.pack(pady=(30, 10))
        
        # Versione
        version_label = tk.Label(about_window, text=VERSION, 
                               font=(FONT_FAMILY, 14),
                               fg=C64_PALETTE["CYAN"],
                               bg=C64_PALETTE["BLACK"])
        version_label.pack(pady=(0, 10))
        
        # Autore
        author_label = tk.Label(about_window, text="Author: ezrad & IA", 
                               font=(FONT_FAMILY, 12),
                               fg=C64_PALETTE["WHITE"],
                               bg=C64_PALETTE["BLACK"])
        author_label.pack(pady=(0, 10))
        
        # Anno
        year_label = tk.Label(about_window, text="2026", 
                             font=(FONT_FAMILY, 12),
                             fg=C64_PALETTE["YELLOW"],
                             bg=C64_PALETTE["BLACK"])
        year_label.pack(pady=(0, 10))
        
        # Descrizione
        desc_label = tk.Label(about_window, 
                             text="C64 SID Music Player\nwith C64 cover art support\nvia IGDB & RAWG APIs",
                             font=(FONT_FAMILY, 10),
                             fg=C64_PALETTE["LIGHT_GREY"],
                             bg=C64_PALETTE["BLACK"])
        desc_label.pack(pady=(20, 10))
        
        # Pulsante di chiusura
        close_btn = tk.Button(about_window, text="CLOSE", 
                             command=about_window.destroy,
                             font=(FONT_FAMILY, 12, "bold"),
                             fg=C64_PALETTE["BLACK"],
                             bg=C64_PALETTE["LIGHT_BLUE"],
                             padx=20, pady=5, anchor="center")
        close_btn.pack(pady=(20, 0))
        
        # Centra la finestra
        about_window.transient(self.master)
        about_window.grab_set()
        about_window.focus_set()
        
        # Centra la finestra rispetto alla finestra principale
        x = self.master.winfo_x() + (self.master.winfo_width() // 2) - (400 // 2)
        y = self.master.winfo_y() + (self.master.winfo_height() // 2) - (300 // 2)
        about_window.geometry(f"400x300+{x}+{y}")
    
    def quit_all(self):
        if self.current_process:
            try:
                self.current_process.terminate()
            except:
                pass
        self.master.destroy()

def main():
    # Verifica se PIL/Pillow è installato
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("ATTENZIONE: Pillow non è installato.")
        print("Le immagini dei videogiochi non potranno essere mostrate.")
        print("Installa con: pip install Pillow")
        
        # Crea una versione senza supporto immagini
        global SidTkPlayer
        original_init = SidTkPlayer.__init__
        def patched_init(self, master):
            original_init(self, master)
            # Modifica l'interfaccia per mostrare messaggio invece di immagine
            self.image_label.config(text="[Install Pillow for game images]", 
                                  font=(FONT_FAMILY, 10),
                                  fg=C64_PALETTE["RED"],
                                  bg=C64_PALETTE["BLACK"])
        
        SidTkPlayer.__init__ = patched_init
    
    root = tk.Tk()
    
    # Leggi API key RAWG
    rawg_api_key = os.environ.get('RAWG_API_KEY')
    if not rawg_api_key:
        api_key_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rawg_api_key.txt")
        if os.path.exists(api_key_file):
            try:
                with open(api_key_file, 'r') as f:
                    rawg_api_key = f.read().strip()
            except:
                pass
    
    # Leggi credenziali IGDB (RACCOMANDATO)
    igdb_client_id = os.environ.get('IGDB_CLIENT_ID')
    igdb_access_token = os.environ.get('IGDB_ACCESS_TOKEN')
    
    if not igdb_client_id or not igdb_access_token:
        igdb_cred_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "igdb_credentials.txt")
        if os.path.exists(igdb_cred_file):
            try:
                with open(igdb_cred_file, 'r') as f:
                    lines = f.read().strip().splitlines()
                    if len(lines) >= 2:
                        igdb_client_id = lines[0].strip()
                        igdb_access_token = lines[1].strip()
            except:
                pass
    
    # Messaggi informativi
    if rawg_api_key:
        print(f"API Key RAWG trovata")
    else:
        print("API Key RAWG non trovata. RAWG disabilitato.")
    
    if igdb_client_id and igdb_access_token:
        print(f"Credenziali IGDB trovate - Copertine C64 abilitate!")
        print(f"Client ID: {igdb_client_id[:10]}...")
        print(f"Access Token: {igdb_access_token[:10]}...")
    else:
        print("Credenziali IGDB non trovate. Per copertine accurate:")
        print("1. Vai su https://api-docs.igdb.com/#authentication")
        print("2. Ottieni Client ID e Access Token")
        print("3. Salva in 'igdb_credentials.txt' (2 righe)")
    
    app = SidTkPlayer(root, 
                     rawg_api_key=rawg_api_key,
                     igdb_client_id=igdb_client_id,
                     igdb_access_token=igdb_access_token)
    root.mainloop()

if __name__ == "__main__":
    main()
