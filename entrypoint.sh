#!/usr/bin/env bash
set -e

# Ensure persistent directories exist
mkdir -p /data/tools
mkdir -p /data/templates
mkdir -p /data/logs
mkdir -p /data/users

# Keep users dir visible in volume browsers before first profile is created.
touch /data/users/.keep

# Bootstrap: copy defaults only when target file is missing.
# This keeps user-customized files intact while adding new shipped files.
sync_missing_files() {
    local src_dir="$1"
    local dst_dir="$2"
    local pattern="$3"

    shopt -s nullglob
    for src in "$src_dir"/$pattern; do
        local name
        name="$(basename "$src")"
        if [ ! -e "$dst_dir/$name" ]; then
            echo "[entrypoint] Copying missing default: $dst_dir/$name"
            cp "$src" "$dst_dir/$name"
        fi
    done
    shopt -u nullglob
}

sync_missing_files /app/tools /data/tools "*.py"
sync_missing_files /app/templates /data/templates "*.md"

exec python server.py
