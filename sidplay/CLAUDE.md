# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Normal launch
python sidplay.py

# With debug output to terminal
python sidplay.py -d

# Show help
python sidplay.py -h

# Monitor log in real time
tail -f sidplayer_debug.log
```

## Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
# Required: Pillow, requests

# Install system SID player (macOS)
brew install sidplay

# Install system SID player (Linux Debian/Ubuntu)
sudo apt install sidplay
```

## Configuration

Copy `sidplayer.cfg.example` to `sidplayer.cfg` to customize paths, API keys, window size, and the sidplayfp command. The app runs without a config file using built-in defaults.

## Architecture

The application is a Tkinter GUI SID file player for Commodore 64 music. It has two source files:

- **`sidplay.py`** — Main application (~1400 lines), contains four classes:
  - `Config` — Reads/writes `sidplayer.cfg` using `configparser`; provides typed getters with defaults
  - `RAWGGameImages` — Fetches game cover art from RAWG.io REST API; caches images locally
  - `IGDBGameImages` — Fetches game cover art from IGDB API (requires Twitch/OAuth token); caches images locally
  - `SidTkPlayer` — Main GUI class; owns the Tk root, playlist state, and controls playback by spawning `sidplayfp` as a subprocess. Manages a `self.current_process` handle for stop/skip. Uses `self.root.after()` for non-blocking progress polling.

- **`stil_reader.py`** — Standalone `STILReader` class that parses HVSC `STIL.txt` (SID Tune Information List) to provide per-subsong titles and comments. Searched automatically at `~/Music/HVSC/STIL.txt`, `~/HVSC/STIL.txt`, or a path in config.

### Key Data Flow

1. User loads SID files or a `playlist.txt` via the GUI
2. `SidTkPlayer` parses each entry as `filepath[:subsong_number]`
3. On play, spawns `sidplayfp` subprocess; `STILReader` supplies the subsong title
4. Cover art is fetched from IGDB (preferred) or RAWG using the SID filename as a search query, then cached in `images_dir`
5. Images are displayed using `PIL.ImageTk.PhotoImage` scaled to fit the display canvas

### Playlist Format

```
# Comments start with #
/path/to/file.sid
/path/to/file.sid:2   # specific subsong
```

### Logging

Debug messages always go to `sidplayer_debug.log` in the script directory. Pass `-d` to also print them to stdout.
