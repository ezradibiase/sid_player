#!/usr/bin/env python3
"""
Test per estrarre e mostrare le info STIL dai file SID
"""

import os
import re
from pathlib import Path

class STILReader:
    """
    Legge e parsifica il file STIL.txt (SID Tune Information List)
    Fornisce informazioni sui sub-tune specifici
    """
    
    def __init__(self, stil_path=None):
        """
        Inizializza il lettore STIL
        
        Args:
            stil_path: Percorso del file STIL.txt. Se None, cerca nelle posizioni comuni
        """
        self.entries = {}  # {normalized_path: {'#1': {...}, '#2': {...}}}
        self.loaded = False
        
        if stil_path is None:
            stil_path = self._find_stil_file()
        
        if stil_path and os.path.exists(stil_path):
            self.load(stil_path)
    
    def _find_stil_file(self):
        """Cerca il file STIL.txt in posizioni comuni"""
        possible_paths = [
            'STIL.txt',
            os.path.expanduser('~/Music/HVSC/STIL.txt'),
            os.path.expanduser('~/HVSC/STIL.txt'),
            '/usr/share/HVSC/STIL.txt',
        ]
        
        # Cerca nella directory dello script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.insert(0, os.path.join(script_dir, 'STIL.txt'))
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"STIL.txt trovato: {path}")
                return path
        
        print("STIL.txt non trovato")
        return None
    
    def load(self, stil_path):
        """
        Carica e parsifica il file STIL.txt
        
        Formato STIL:
        /MUSICIANS/H/Hubbard_Rob/Commando.sid
           TITLE: Commando (Title Screen)
        #2 TITLE: Commando (In-Game)
           COMMENT: Rob's masterpiece...
        """
        print(f"Caricamento STIL da: {stil_path}")
        
        try:
            with open(stil_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"Errore lettura STIL: {e}")
            return False
        
        # Dividi per entry (ogni entry inizia con un percorso che inizia con /)
        # Le entry sono separate da linee vuote multiple
        current_path = None
        current_entry = {}
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Salta linee vuote
            if not stripped:
                i += 1
                continue
            
            # Nuova entry: linea che inizia con /
            if stripped.startswith('/'):
                # Salva l'entry precedente se esiste
                if current_path:
                    self._save_entry(current_path, current_entry)
                
                # Inizia nuova entry
                current_path = stripped
                current_entry = {}
                i += 1
                continue
            
            # Linea di campo (TITLE, COMMENT, ecc.)
            if current_path and ':' in stripped:
                # Determina il numero di subsong (es. "#2 TITLE:" -> subsong 2)
                subsong_num = 1  # Default: subsong 1
                
                match = re.match(r'^#(\d+)\s+(\w+):\s*(.*)$', stripped)
                if match:
                    subsong_num = int(match.group(1))
                    field_name = match.group(2)
                    field_value = match.group(3)
                else:
                    # Nessun prefisso #N, si applica al subsong 1 o è generico
                    match = re.match(r'^(\w+):\s*(.*)$', stripped)
                    if match:
                        field_name = match.group(1)
                        field_value = match.group(2)
                    else:
                        i += 1
                        continue
                
                # Salva nel formato: {'#1': {'TITLE': '...', 'COMMENT': '...'}}
                key = f'#{subsong_num}'
                if key not in current_entry:
                    current_entry[key] = {}
                
                # Se il field_value continua nelle linee successive (multiline)
                while i + 1 < len(lines) and lines[i + 1].strip() and not lines[i + 1].strip().startswith('/') and not re.match(r'^#?\d*\s*\w+:', lines[i + 1].strip()):
                    i += 1
                    field_value += ' ' + lines[i].strip()
                
                current_entry[key][field_name] = field_value.strip()
            
            i += 1
        
        # Salva l'ultima entry
        if current_path:
            self._save_entry(current_path, current_entry)
        
        self.loaded = True
        print(f"STIL caricato: {len(self.entries)} entry")
        return True
    
    def _save_entry(self, path, entry):
        """Salva un'entry normalizzando il percorso"""
        # Normalizza il percorso per la ricerca
        normalized = self._normalize_path(path)
        self.entries[normalized] = entry
    
    def _normalize_path(self, path):
        """
        Normalizza un percorso per la ricerca
        
        Gestisce varianti come:
        - /MUSICIANS/H/Hubbard_Rob/Commando.sid
        - Commando.sid
        - /H/Hubbard_Rob/Commando.sid
        """
        # Rimuovi spazi e normalizza
        path = path.strip()
        
        # Converti underscore in spazi per confronti più flessibili
        # Ma mantieni il percorso originale per la chiave
        return path.lower()
    
    def get_info(self, sid_path, subsong=1):
        """
        Ottiene le informazioni STIL per un file SID e subsong specifico
        
        Args:
            sid_path: Percorso del file SID (assoluto o solo nome)
            subsong: Numero del subsong (default: 1)
        
        Returns:
            dict con TITLE, COMMENT, ecc. o None se non trovato
        """
        if not self.loaded:
            return None
        
        # Estrai solo il nome del file dal percorso completo
        sid_filename = os.path.basename(sid_path)
        
        # Cerca per nome file esatto
        normalized_search = sid_filename.lower()
        
        # Prova diverse strategie di ricerca
        for normalized_path, entry in self.entries.items():
            # Estrai il nome file dal path STIL
            stil_filename = os.path.basename(normalized_path)
            
            if stil_filename == normalized_search:
                # Trovato! Ora cerca il subsong specifico
                key = f'#{subsong}'
                
                # Prima prova il subsong specifico
                if key in entry:
                    return entry[key]
                
                # Se non c'è il subsong specifico, prova #1 come fallback
                if '#1' in entry:
                    return entry['#1']
                
                # Se non c'è nemmeno #1, prendi la prima entry disponibile
                if entry:
                    first_key = next(iter(entry))
                    return entry[first_key]
        
        return None
    
    def get_title(self, sid_path, subsong=1, fallback_to_filename=True):
        """
        Ottiene il titolo STIL per un file SID
        
        Args:
            sid_path: Percorso del file SID
            subsong: Numero del subsong
            fallback_to_filename: Se True, usa il nome file se STIL non trovato
        
        Returns:
            Titolo della traccia o None
        """
        info = self.get_info(sid_path, subsong)
        
        if info and 'TITLE' in info:
            return info['TITLE']
        
        if fallback_to_filename:
            # Fallback: estrai dal nome file
            name = os.path.basename(sid_path)
            if name.lower().endswith('.sid'):
                name = name[:-4]
            return name.replace('_', ' ')
        
        return None
    
    def get_comment(self, sid_path, subsong=1):
        """Ottiene il commento STIL per un file SID"""
        info = self.get_info(sid_path, subsong)
        return info.get('COMMENT') if info else None
    
    def has_info(self, sid_path, subsong=1):
        """Controlla se esistono informazioni STIL per questo file/subsong"""
        return self.get_info(sid_path, subsong) is not None


def test_stil():
    """Test del lettore STIL"""
    print("=" * 60)
    print("STIL Reader Test")
    print("=" * 60)
    
    reader = STILReader()
    
    if not reader.loaded:
        print("STIL non caricato, test saltato")
        return
    
    # Test con alcuni file di esempio
    test_files = [
        ('/MUSICIANS/H/Hubbard_Rob/Commando.sid', 1),
        ('/MUSICIANS/H/Hubbard_Rob/Commando.sid', 2),
        ('/MUSICIANS/H/Hubbard_Rob/Commando.sid', 3),
        ('Commando.sid', 1),
    ]
    
    for path, subsong in test_files:
        info = reader.get_info(path, subsong)
        if info:
            print(f"\n{path} (subsong {subsong}):")
            print(f"  TITLE: {info.get('TITLE', 'N/A')}")
            print(f"  COMMENT: {info.get('COMMENT', 'N/A')[:50]}..." if info.get('COMMENT') else None)
        else:
            print(f"\n{path} (subsong {subsong}): Nessuna info STIL")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_stil()
