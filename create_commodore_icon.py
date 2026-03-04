#!/usr/bin/env python3
"""
Script per creare un'icona Commodore C= base in formato PNG.
L'immagine generata può essere convertita in .icns usando create_icns.sh
"""

from PIL import Image, ImageDraw

# Crea un'immagine 512x512 con sfondo blu C64
img_size = 512
bg_color = (56, 59, 240)  # C64 blue #383BF0
logo_color = (255, 255, 255)  # White

img = Image.new('RGB', (img_size, img_size), bg_color)
draw = ImageDraw.Draw(img)

# Disegna il logo Commodore "C=" stilizzato
# Centro dell'immagine
cx, cy = img_size // 2, img_size // 2

# Dimensioni del logo
logo_width = 300
logo_height = 200
line_thickness = 35

# Disegna la "C"
# Parte superiore
draw.arc([cx - logo_width//2, cy - logo_height//2, 
          cx + logo_width//2, cy + logo_height//2],
         start=45, end=315, fill=logo_color, width=line_thickness)

# Disegna le due linee "="
line_length = 120
line_y_offset = 20

# Linea superiore
draw.line([(cx + 40, cy - line_y_offset), 
           (cx + 40 + line_length, cy - line_y_offset)], 
          fill=logo_color, width=line_thickness//2)

# Linea inferiore
draw.line([(cx + 40, cy + line_y_offset), 
           (cx + 40 + line_length, cy + line_y_offset)], 
          fill=logo_color, width=line_thickness//2)

# Salva l'immagine
output_file = "commodore.png"
img.save(output_file, 'PNG')
print(f"✓ Icona creata: {output_file} ({img_size}x{img_size})")
print(f"  Ora puoi convertirla in .icns con:")
print(f"  ./create_icns.sh")
