#!/bin/bash
# Script per creare un'App Bundle macOS per SIDPlayer

APP_NAME="SIDPlayer"
APP_DIR="${APP_NAME}.app"
SCRIPT_PATH="sid_play5.py"
ICON_FILE="commodore.icns"
CONFIG_FILE="sidplayer.cfg"

# Trova il percorso di Python3 con le librerie installate
PYTHON_PATH=$(which python3)

echo "=== Creazione App Bundle: ${APP_NAME}.app ==="
echo ""
echo "Python utilizzato: $PYTHON_PATH"

# Verifica che lo script esista
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "✗ Errore: $SCRIPT_PATH non trovato"
    exit 1
fi

# Verifica che l'icona esista
if [ ! -f "$ICON_FILE" ]; then
    echo "✗ Errore: $ICON_FILE non trovato"
    echo "  Esegui prima: python3 create_commodore_icon.py && ./create_icns.sh"
    exit 1
fi

# Crea la struttura dell'app bundle
echo "Creazione struttura app bundle..."
mkdir -p "${APP_DIR}/Contents/MacOS"
mkdir -p "${APP_DIR}/Contents/Resources"

# Copia l'icona
cp "$ICON_FILE" "${APP_DIR}/Contents/Resources/"

# Copia la playlist (se esiste) - dentro l'app bundle
if [ -f "playlist.txt" ]; then
    cp "playlist.txt" "${APP_DIR}/Contents/MacOS/"
    echo "✓ Playlist inclusa: playlist.txt"
fi

# Copia il banner (se esiste) - dentro l'app bundle e config utente
if [ -f "sidplayer_banner.png" ]; then
    cp "sidplayer_banner.png" "${APP_DIR}/Contents/MacOS/"
    echo "✓ Banner incluso nell'app"
fi

# Crea la directory di configurazione utente e copia i file (se esistono)
USER_CONFIG_DIR="$HOME/Library/Application Support/SIDPlayer"
if [ -f "$CONFIG_FILE" ]; then
    mkdir -p "$USER_CONFIG_DIR"
    cp "$CONFIG_FILE" "$USER_CONFIG_DIR/"
    echo "✓ Configurazione installata in: $USER_CONFIG_DIR"
fi

if [ -f "sidplayer_banner.png" ]; then
    mkdir -p "$USER_CONFIG_DIR"
    cp "sidplayer_banner.png" "$USER_CONFIG_DIR/"
    echo "✓ Banner installato in: $USER_CONFIG_DIR"
fi
echo "  (puoi modificare i file senza ricostruire l'app)"

# Crea il file PkgInfo
echo "APPL????" > "${APP_DIR}/Contents/PkgInfo"

# Crea il file Info.plist
cat > "${APP_DIR}/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch.sh</string>
    <key>CFBundleIdentifier</key>
    <string>com.ezrad.sidplayer</string>
    <key>CFBundleName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleDisplayName</key>
    <string>${APP_NAME}</string>
    <key>CFBundleIconFile</key>
    <string>commodore</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.2</string>
    <key>CFBundleVersion</key>
    <string>2.2.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
EOF

# Crea lo script di lancio con il percorso corretto di Python
cat > "${APP_DIR}/Contents/MacOS/launch.sh" << EOF
#!/bin/bash
# Script di lancio per \${APP_NAME}

SCRIPT_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
APP_DIR="\$(dirname "\$SCRIPT_DIR")"
LOG_FILE="\${SCRIPT_DIR}/sidplayer.log"

# Log avvio
echo "=== SIDPlayer Launch Log ===" > "\$LOG_FILE"
echo "Data: \$(date)" >> "\$LOG_FILE"
echo "Python: $PYTHON_PATH" >> "\$LOG_FILE"
echo "" >> "\$LOG_FILE"

# Esegui lo script Python
cd "\${APP_DIR}/.."
"$PYTHON_PATH" "\${SCRIPT_DIR}/sid_play5.py" >> "\$LOG_FILE" 2>&1
EXIT_CODE=\$?

echo "" >> "\$LOG_FILE"
echo "Exit code: \$EXIT_CODE" >> "\$LOG_FILE"

if [ \$EXIT_CODE -ne 0 ]; then
    echo "ERRORE: Applicazione chiusa con codice \$EXIT_CODE"
    tail -30 "\$LOG_FILE"
fi

exit \$EXIT_CODE
EOF

chmod +x "${APP_DIR}/Contents/MacOS/launch.sh"

# Copia lo script Python nell'app bundle
cp "$SCRIPT_PATH" "${APP_DIR}/Contents/MacOS/"

echo ""
echo "✓ App Bundle creata: ${APP_DIR}"
echo ""
echo "Per avviare l'applicazione:"
echo "  open ${APP_DIR}"
echo ""
echo "Oppure fai doppio-click sul file ${APP_DIR} nel Finder"
echo ""
echo "In caso di errore, controlla: ${APP_DIR}/Contents/MacOS/sidplayer.log"
