#!/bin/bash
PID_FILE="/tmp/catlock.pid"
SCRIPT_PATH="/home/brunolmadeira/Projetos/catlock/catlock.py"

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
