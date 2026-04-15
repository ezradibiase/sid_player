#!/bin/bash
# Script per creare la versione standalone di SIDPlayer

APP_NAME="SIDPlayer"
VERSION="2.2"
DIST_DIR="dist"
BUILD_DIR="build"

echo "=== Build SIDPlayer Standalone v${VERSION} ==="
echo ""

# Verifica PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller non installato!"
    echo "Installa con: pip3 install pyinstaller"
    exit 1
fi

# Pulisci build precedenti
echo "🧹 Pulizia build precedenti..."
rm -rf "$DIST_DIR" "$BUILD_DIR"
rm -rf "${APP_NAME}_StandAlone.app"
rm -f "${APP_NAME}_v${VERSION}_Mac.zip"

# Esegui PyInstaller
echo ""
echo "🔨 Compilazione con PyInstaller..."
pyinstaller --onefile \
  --windowed \
  --icon=commodore.icns \
  --name="$APP_NAME" \
  --add-data "sidplayer_banner.png:." \
  --add-data "playlist.txt:." \
  sid_play5.py

if [ $? -ne 0 ]; then
    echo "❌ Errore nella compilazione!"
    exit 1
fi

# Verifica l'eseguibile
if [ ! -f "$DIST_DIR/$APP_NAME" ]; then
    echo "❌ Eseguibile non trovato!"
    exit 1
fi

echo ""
echo "✓ Eseguibile creato: $DIST_DIR/$APP_NAME"
ls -lh "$DIST_DIR/$APP_NAME"

# Crea App Bundle standalone
echo ""
echo "📦 Creazione App Bundle standalone..."

mkdir -p "${APP_NAME}_StandAlone.app/Contents/MacOS"
mkdir -p "${APP_NAME}_StandAlone.app/Contents/Resources"

# Copia eseguibile
cp "$DIST_DIR/$APP_NAME" "${APP_NAME}_StandAlone.app/Contents/MacOS/"

# Copia icona
cp commodore.icns "${APP_NAME}_StandAlone.app/Contents/Resources/"

# Crea Info.plist
cat > "${APP_NAME}_StandAlone.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>$APP_NAME</string>
    <key>CFBundleIconFile</key>
    <string>commodore</string>
    <key>CFBundleIdentifier</key>
    <string>com.ezrad.sidplayer.standalone</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
    <key>CFBundleDisplayName</key>
    <string>$APP_NAME C64</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>$VERSION</string>
    <key>CFBundleVersion</key>
    <string>$VERSION.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

echo "✓ App Bundle creato: ${APP_NAME}_StandAlone.app"

# Crea cartella di distribuzione
echo ""
echo "📁 Preparazione cartella di distribuzione..."

DIST_FOLDER="${APP_NAME}_v${VERSION}_Mac"
mkdir -p "$DIST_FOLDER"

# Copia app bundle
cp -r "${APP_NAME}_StandAlone.app" "$DIST_FOLDER/"

# Copia README
cp README.md "$DIST_FOLDER/"

# Copia sidplayer.cfg.example
cp sidplayer.cfg.example "$DIST_FOLDER/"

# Crea file di istruzioni
cat > "$DIST_FOLDER/LEGGIMI.txt" << EOF
SIDPlayer C64 v${VERSION} - Versione Standalone
============================================

QUESTA VERSIONE NON RICHIEDE INSTALLAZIONE! 🎉

Per avviare l'applicazione:
1. Fai doppio-click su "${APP_NAME}_StandAlone.app"
2. Oppure esegui da terminale: open ${APP_NAME}_StandAlone.app

Configurazione:
- La prima volta che avvii l'app, viene creata automaticamente
  la cartella di configurazione in:
  ~/Library/Application Support/SIDPlayer/

- Puoi modificare la configurazione copiando il file
  sidplayer.cfg.example in:
  ~/Library/Application Support/SIDPlayer/sidplayer.cfg

Requisiti:
- macOS 10.13 o superiore
- sidplayfp installato (brew install sidplayfp)

Per ulteriori informazioni, leggi README.md

Buon ascolto! 🎵🕹️
EOF

echo "✓ Cartella di distribuzione pronta: $DIST_FOLDER/"

# Mostra dimensioni
echo ""
echo "📊 Dimensioni:"
echo "--------------"
du -sh "$DIST_DIR/$APP_NAME"
du -sh "${APP_NAME}_StandAlone.app"
du -sh "$DIST_FOLDER"

echo ""
echo "✅ Build completata con successo!"
echo ""
echo "Per distribuire:"
echo "  1. Comprimi la cartella: zip -r ${APP_NAME}_v${VERSION}.zip $DIST_FOLDER/"
echo "  2. Oppure copia solo l'app: cp -r ${APP_NAME}_StandAlone.app /Applications/"
echo ""
