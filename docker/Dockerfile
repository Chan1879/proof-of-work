FROM python:3.12-slim-bookworm

WORKDIR /app

COPY requirements-lock.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-lock.txt

# Infrastructure modules (baked into image, not hot-swappable)
COPY policies/ policies/
COPY server.py .
COPY engine/ engine/
COPY helpers/ helpers/

# Default tool plugins (staged in image, synced to /data/tools at runtime)
COPY tools/ /app/tools/

# Default templates (staged in image, synced to /data/templates at runtime)
COPY templates/ /app/templates/

# Entrypoint script — ensures /data dirs exist and syncs missing defaults
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Runtime healthcheck script validates persistent data bootstrap
COPY docker/healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Persistent data directory: tools (hot-swappable) + templates + logs + per-user data
RUN mkdir -p /data/tools /data/templates /data/logs /data/users
VOLUME ["/data"]

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV POLICY_PACK_PATH=/app/policies/policy-rules.yaml
ENV CONTRACTS_PATH=/app/policies/tool-contracts.json
ENV AUDIT_LOG_PATH=/data/logs/audit.jsonl
ENV LOG_DIR=/data/logs
ENV TOOLS_DIR=/data/tools
ENV USERS_DIR=/data/users

EXPOSE 5359

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

ENTRYPOINT ["bash", "entrypoint.sh"]
