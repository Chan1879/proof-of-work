# docker/ — Docker Deployment

Docker configuration for building and running the MCP resume server as a container.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build for Python 3.12 slim image |
| `docker-compose.yml` | Single-service Compose config for quick deployment |
| `healthcheck.sh` | Container health check script |

## Quick Start

```bash
# From the project root:
docker compose -f docker/docker-compose.yml up --build -d

# Check container health:
docker ps  # Should show "healthy" after ~20s

# View logs:
docker logs proof_of_work
```

The server starts on **port 5359** with Streamable HTTP transport.

To override the port:

```bash
MCP_PORT=8080 docker compose -f docker/docker-compose.yml up --build -d
```

This maps `${MCP_PORT}` on host and container and sets `MCP_PORT` inside the container.

## Image Architecture

The Dockerfile uses a layered approach:

1. **Base** — `python:3.12-slim-bookworm`
2. **Dependencies** — `pip install -r requirements-lock.txt`
3. **Infrastructure (baked in)** — `engine/`, `helpers/`, `policies/`, `server.py` — these are part of the image and not modifiable at runtime.
4. **Defaults (hot-swappable)** — `tools/` and `templates/` are staged in `/app/` and synced to `/data/` at first boot. Users can modify files in `/data/tools/` and `/data/templates/` without rebuilding the image.

## Volume Mounts

A single named volume `/data` persists across container restarts:

```
/data/
├── tools/       ← Hot-swappable tool plugins (synced from /app/tools/ on first boot)
├── templates/   ← Customizable templates (synced from /app/templates/ on first boot)
├── logs/        ← Audit log (audit.jsonl) and server log (server.log)
└── users/       ← Per-user data directories (skills, preferences, history)
```

## Environment Variables

See the main [README](../README.md#configuration) for the full list. Key variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `TOOLS_DIR` | `/data/tools` | Directory scanned for tool plugins |
| `USERS_DIR` | `/data/users` | Per-user data storage root |
| `AUDIT_LOG_PATH` | `/data/logs/audit.jsonl` | Path to audit log file |
| `LOG_DIR` | `/data/logs` | Server log directory |
| `MCP_PORT` | `5359` | MCP HTTP listener port |

## Health Check

`healthcheck.sh` runs every 30 seconds and validates:

1. `/data/tools/` directory exists
2. `/data/templates/` directory exists
3. `/data/users/` directory exists
4. At least one `.py` file in `/data/tools/` (tool loaded)
5. At least one `.md` file in `/data/templates/` (template loaded)

If any check fails, the container is marked unhealthy.

## Hot-Swapping Tools & Templates

The `entrypoint.sh` script syncs missing default files from `/app/` to `/data/` at boot. It only copies files that don't already exist, preserving any user customizations.

To add a custom tool:
1. Write a `.py` file exporting a `TOOL_DEF` dict (see [tools/README.md](../tools/README.md#tool-plugins)).
2. Copy it into the running container's `/data/tools/` directory.
3. Restart the container — the server will load it automatically.
