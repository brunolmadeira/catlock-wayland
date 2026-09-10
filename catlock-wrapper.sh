#!/bin/bash
PID_FILE="/tmp/catlock.pid"

# Localiza o diretório deste script dinamicamente (compatível com qualquer caminho ou symlink)
SCRIPT_DIR="$(dirname "$(realpath "$0" 2>/dev/null || readlink -f "$0" 2>/dev/null || echo "$(cd "$(dirname "$0")" && pwd)")")"
SCRIPT_PATH="$SCRIPT_DIR/catlock.py"

# Se já estiver rodando, encerra (toggle)
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -TERM "$PID" 2>/dev/null
        exit 0
    fi
fi

# Inicia a interface gráfica do CatLock diretamente no usuário da sessão
exec python3 "$SCRIPT_PATH" "$@"
