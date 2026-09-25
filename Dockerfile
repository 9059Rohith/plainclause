FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.ts tsconfig.json ./
COPY src ./src
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl zstd libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ARG OLLAMA_VERSION=0.34.3
RUN curl -fsSL "https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tar.zst" \
      | tar --zstd -x -C /usr \
    && rm -rf /usr/lib/ollama/cuda* /usr/lib/ollama/vulkan* /usr/lib/ollama/rocm* /usr/lib/ollama/mlx*

COPY backend/requirements.lock.txt backend/requirements.production.txt /app/backend/
RUN python -m pip install --no-cache-dir -r /app/backend/requirements.production.txt

ENV OLLAMA_HOST=127.0.0.1:11434 \
    OLLAMA_MODELS=/opt/ollama-models \
    OLLAMA_NUM_PARALLEL=1 \
    OLLAMA_MAX_LOADED_MODELS=1 \
    OLLAMA_KEEP_ALIVE=0 \
    PLAINCLAUSE_HOSTED_SERVICE=1 \
    PLAINCLAUSE_DB_PATH=/data/plainclause.db \
    PYTHONPATH=/app/backend

RUN set -eu; \
    ollama serve >/tmp/ollama-build.log 2>&1 & server_pid=$!; \
    trap 'kill "$server_pid" 2>/dev/null || true' EXIT; \
    for attempt in $(seq 1 60); do \
      if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null; then break; fi; \
      sleep 1; \
    done; \
    ollama pull qwen2.5:1.5b; \
    ollama pull all-minilm; \
    kill "$server_pid" 2>/dev/null || true; \
    wait "$server_pid" 2>/dev/null || true

COPY backend/app /app/backend/app
COPY --from=frontend /app/dist /app/dist
COPY deployment/start.sh /app/deployment/start.sh
RUN chmod +x /app/deployment/start.sh

EXPOSE 8000
ENTRYPOINT ["/app/deployment/start.sh"]
