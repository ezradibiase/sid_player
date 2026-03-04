#!/bin/bash
# Script per convertire PNG in ICNS per macOS

INPUT_PNG="commodore.png"
OUTPUT_ICNS="commodore.icns"
ICONSET_DIR="commodore.iconset"

if [ ! -f "$INPUT_PNG" ]; then
    echo "Errore: $INPUT_PNG non trovato!"
    echo ""
    echo "Crea prima l'immagine PNG con:"
    echo "  python3 create_commodore_icon.py"
    echo ""
    echo "Oppure fornisci un'immagine PNG 512x512 del logo Commodore"
    exit 1
fi

# Crea la cartella .iconset
mkdir -p "$ICONSET_DIR"

# Genera tutte le dimensioni richieste
echo "Generazione icone..."
sips -z 512 512 "$INPUT_PNG" --out "$ICONSET_DIR/icon_512x512.png" 2>/dev/null
sips -z 256 256 "$INPUT_PNG" --out "$ICONSET_DIR/icon_256x256.png" 2>/dev/null
sips -z 128 128 "$INPUT_PNG" --out "$ICONSET_DIR/icon_128x128.png" 2>/dev/null
sips -z 64 64 "$INPUT_PNG" --out "$ICONSET_DIR/icon_64x64.png" 2>/dev/null
sips -z 32 32 "$INPUT_PNG" --out "$ICONSET_DIR/icon_32x32.png" 2>/dev/null
sips -z 16 16 "$INPUT_PNG" --out "$ICONSET_DIR/icon_16x16.png" 2>/dev/null

# Crea le versioni @2x (Retina)
cp "$ICONSET_DIR/icon_256x256.png" "$ICONSET_DIR/icon_128x128@2x.png"
cp "$ICONSET_DIR/icon_512x512.png" "$ICONSET_DIR/icon_256x256@2x.png"

# Converte in .icns usando iconutil (tool di macOS)
echo "Creazione file ICNS..."
iconutil -c icns "$ICONSET_DIR" -o "$OUTPUT_ICNS"

if [ $? -eq 0 ]; then
    # Pulisci la cartella temporanea
    rm -rf "$ICONSET_DIR"
    echo ""
    echo "✓ Fatto! Icona creata: $OUTPUT_ICNS"
    echo "  Ora avvia il programma per vedere l'icona nel dock."
else
    echo ""
    echo "✗ Errore nella creazione dell'icona ICNS"
    echo "  Assicurati di essere su macOS con Xcode installato"
    rm -rf "$ICONSET_DIR"
    exit 1
fi
