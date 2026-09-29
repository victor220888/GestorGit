#!/bin/bash
# Lanzador para GestorGit en Linux
# Ejecuta principal.py con Python 3

# Obtener el directorio donde está este script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$DIR" || exit 1

# Verificar que python3 esté disponible
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 no está instalado."
    echo "Instalalo con: sudo apt install python3 python3-tk"
    read -p "Presioná Enter para salir..."
    exit 1
fi

# Verificar que tkinter esté disponible
if ! python3 -c "import tkinter" &> /dev/null; then
    echo "Error: falta el módulo tkinter."
    echo "Instalalo con: sudo apt install python3-tk"
    read -p "Presioná Enter para salir..."
    exit 1
fi

# Ejecutar GestorGit
python3 "$DIR/principal.py"
