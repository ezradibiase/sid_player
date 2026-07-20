#!/usr/bin/env python3
"""
Lettore del database GB64 (GameBase64) per identificare con precisione
la cover art ufficiale di un gioco, invece di indovinarla dal nome file.

Stesso approccio usato da DeepSID: importa il database GB64 (GBC_vNN.mdb)
invece di indovinare per euristiche sul nome — un GA_Id preciso invece di
un nome file "probabile". Il file .mdb (Access) viene letto tramite
mdbtools (mdb-export), l'unico modo pratico e cross-platform di leggerlo
senza driver Access proprietari.
"""

import csv
import os
import shutil
import subprocess


class GB64Database:
    """
    Legge le tabelle Games ed Extras dal database GB64 e fornisce una mappa
    titolo SID -> path relativo della cover ufficiale (dentro la cartella
    "Cover" della collezione locale dell'utente).
    """

    def __init__(self, mdb_path=None):
        self.loaded = False
        self._games = []            # [(nome, GA_Id), ...]
        self._covers_by_gaid = {}   # GA_Id -> [path relativo, ...]

        if mdb_path and os.path.exists(mdb_path):
            self.load(mdb_path)

    def load(self, mdb_path):
        """Carica ed indicizza il database. Non solleva eccezioni: se qualcosa
        va storto (mdbtools mancante, file corrotto...) resta semplicemente
        self.loaded = False, e il chiamante userà i fallback online."""
        if not shutil.which('mdb-export'):
            print("mdb-export non trovato (serve mdbtools) — database GB64 disabilitato")
            return

        try:
            games_rows = self._export_table(mdb_path, 'Games')
            extras_rows = self._export_table(mdb_path, 'Extras')
        except Exception as e:
            print(f"Errore lettura database GB64 ({mdb_path}): {e}")
            return

        self._games = [
            (r['Name'], r['GA_Id']) for r in games_rows
            if r.get('Name') and r.get('GA_Id')
        ]

        for r in extras_rows:
            if r.get('Type') != '0':
                continue
            name = r.get('Name') or ''
            if not name.lower().startswith('cover'):
                continue
            ga_id = r.get('GA_Id')
            path = r.get('Path') or ''
            if not ga_id or not path:
                continue
            # Path tipo "Cover\N\Nome_Gioco.jpg": la cartella locale
            # dell'utente E' GIA' quella "Cover", quindi si toglie il
            # primo segmento e si convertono i backslash.
            parts = path.replace('\\', '/').split('/', 1)
            rel_path = parts[1] if len(parts) > 1 else parts[0]
            self._covers_by_gaid.setdefault(ga_id, []).append(rel_path)

        self.loaded = True
        print(f"Database GB64 caricato: {len(self._games)} giochi, "
              f"{len(self._covers_by_gaid)} con cover disponibile")

    def _export_table(self, mdb_path, table):
        result = subprocess.run(
            ['mdb-export', mdb_path, table],
            capture_output=True, text=True, timeout=60, check=True,
        )
        return list(csv.DictReader(result.stdout.splitlines()))

    def find_cover_relpath(self, sid_title, score_fn, min_score):
        """
        Trova il path relativo (dentro la cartella Cover) della cover
        ufficiale per il titolo dato. `score_fn(nome_candidato, query)` è la
        stessa funzione di scoring già usata per IGDB/RAWG, passata dal
        chiamante per non creare una dipendenza circolare col modulo
        principale. Ritorna None se non c'è un match sopra soglia o se il
        gioco trovato non ha nessuna cover catalogata.
        """
        if not self.loaded or not sid_title:
            return None

        best_score = -1
        best_ga_id = None
        for name, ga_id in self._games:
            if ga_id not in self._covers_by_gaid:
                continue
            score = score_fn(name, sid_title)
            if score > best_score:
                best_score = score
                best_ga_id = ga_id
                if best_score == 100:
                    break  # match esatto, non serve continuare a cercare

        if best_ga_id is None or best_score < min_score:
            return None

        return self._covers_by_gaid[best_ga_id][0]
