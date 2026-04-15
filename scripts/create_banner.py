#!/usr/bin/env python3
"""
Genera un'immagine PNG dall'ASCII art del banner SIDPlayer
"""

from PIL import Image, ImageDraw, ImageFont

# ASCII art del banner (solo la parte grafica, senza testi laterali)
BANNER_ASCII = """⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣿⠛⠋⠁⠉⠙⠿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⢿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠟⠁⠀⣠⣄⣤⣠⣤⣶⣶⣶⣶⣦⣄⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠃⠀⣴⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡄⠈⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡏⠀⢸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⢻⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⣼⠿⠛⠛⠛⠛⠛⢿⣿⣿⣿⡟⠛⠛⠛⠿⣿⡇⠸⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠀⠁⢠⠶⠶⠂⠀⠈⢿⣿⣿⣿⠛⠛⠻⠿⣿⣷⠀⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⡷⢀⣐⣀⣤⣦⣤⣾⣿⣿⣿⣾⣶⣾⣷⣾⣿⣆⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⢡⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿⣿⣿⣿⣿⣿⣿⡿⠛⢿⣟⡻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⠉⡿⣿⣿⣿⡿⠂⠀⠈⠉⠹⢻⣿⣿⣿⣿⣿⢻⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠈⡹⠁⠀⠀⠀⠠⣄⡠⡤⠀⠈⠉⣿⣿⢹⣼⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡀⠀⠀⡤⠐⠶⠾⠿⠿⠿⣶⣶⣬⣿⢇⢈⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⡀⠀⠁⣠⣤⡀⢀⣠⣶⣿⣟⠟⠲⠋⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠙⠙⠛⠿⠿⠋⠋⠁⢀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠿⠄⠀⠀⠀⠀⠀⠀⠀⢀⠀⣠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⣿⣿⣿⣿⣿⣿⣿⣿⡿⠿⠛⠋⠉⠀⠀⠀⠀⣶⣶⣄⠀⠀⠰⣶⣿⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠿⠿⠛⠛⠛⠉⠉⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⣿⣿⣶⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡟⢿⣿⣿⣿⣿
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢻⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣻⣿⣆⠙⢿⣿⣿"""

# Colori
BG_COLOR = (0, 0, 0)  # Nero sfondo
FG_COLOR = (238, 238, 119)  # C64 Yellow (#EEEE77) - giallo tenue

# Dimensioni carattere e padding
FONT_SIZE = 14  # Aumentato per migliore leggibilità
PADDING = 15
LINE_SPACING = 0

def create_banner_image(output_path="sidplayer_banner.png"):
    """Crea l'immagine PNG dal banner ASCII"""

    # Prova font che supportano caratteri Braille/Unicode
    font_paths = [
        "/System/Library/Fonts/Supplemental/Apple Symbols.ttf",  # macOS - ottimo per simboli
        "/System/Library/Fonts/Menlo.ttc",  # macOS - monospace
        "/Library/Fonts/DejaVuSansMono.ttf",  # Font con ottimo supporto Unicode
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",  # Linux alternativo
        "C64Pro-Regular.ttf",  # Font locale
    ]

    font = None
    used_font_path = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, FONT_SIZE)
            # Testa se supporta i caratteri Braille
            test = font.getbbox("⣿")
            used_font_path = font_path
            break
        except:
            continue

    if font is None:
        font = ImageFont.load_default()
        used_font_path = "default"
        print("ℹ Uso font di default (potrebbe non mostrare i caratteri Braille)")
    
    print(f"✓ Font utilizzato: {used_font_path}")

    # Calcola le dimensioni dell'immagine
    lines = BANNER_ASCII.strip().split('\n')
    max_width = 0
    for line in lines:
        bbox = font.getbbox(line)
        width = bbox[2] - bbox[0]
        if width > max_width:
            max_width = width

    img_width = max_width + (PADDING * 2)
    img_height = (len(lines) * (FONT_SIZE + LINE_SPACING)) + (PADDING * 2)

    # Crea l'immagine
    img = Image.new('RGB', (img_width, img_height), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Disegna ogni linea
    y = PADDING
    for line in lines:
        draw.text((PADDING, y), line, font=font, fill=FG_COLOR)
        y += FONT_SIZE + LINE_SPACING

    # Salva l'immagine
    img.save(output_path, 'PNG')
    print(f"✓ Immagine creata: {output_path} ({img_width}x{img_height} pixel)")
    return output_path

if __name__ == "__main__":
    create_banner_image()
