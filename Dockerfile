# --- Stage 1: build the React SPA -------------------------------------------
# Built with VITE_API_BASE="" so it calls the API at same-origin root paths
# (/auth, /content, ...) — the single-port prod layout, not the dev /api proxy.
FROM node:20-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
ENV VITE_API_BASE=""
RUN npm run build

# --- Stage 2: python runtime ------------------------------------------------
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Whisper model cache baked into the image (not the ./data volume) so first boot
# is fast and deterministic — no runtime download on a live host.
ENV HF_HOME=/opt/hf-cache
RUN pip install --no-cache-dir uv

# Speech runtime: libgomp for ctranslate2/onnxruntime (faster-whisper, CPU int8);
# curl/ca-certificates to fetch Piper. PyAV wheels bundle ffmpeg, so no system
# ffmpeg is needed to decode the browser's webm/opus.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libgomp1 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Piper TTS: self-contained binary release (bundles espeak-ng-data + shared libs).
# The adapter shells out to a bare `piper`; the wrapper preserves its $ORIGIN
# library lookup regardless of how it's invoked.
RUN curl -fsSL -o /tmp/piper.tar.gz \
      https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz \
    && tar -xzf /tmp/piper.tar.gz -C /opt \
    && rm /tmp/piper.tar.gz \
    && printf '#!/bin/sh\nexec /opt/piper/piper --espeak_data /opt/piper/espeak-ng-data "$@"\n' > /usr/local/bin/piper \
    && chmod +x /usr/local/bin/piper

# French Piper voice (fr_FR-upmc-medium, ~63 MB). -L follows the HF CDN redirect.
# Piper has no Canadian (fr_CA) voice; upmc is a clearer fr_FR voice than siwis
# (default speaker 0 = "jessica"). See VOICES.md — all French voices are fr_FR.
RUN mkdir -p /app/voices \
    && curl -fsSL -o /app/voices/fr_FR-upmc-medium.onnx \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx \
    && curl -fsSL -o /app/voices/fr_FR-upmc-medium.onnx.json \
      https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium/fr_FR-upmc-medium.onnx.json

WORKDIR /app
# Dependency layer (cached until the lock changes). --no-install-project: install
# deps only; the app runs from the copied source below.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

# Bake the faster-whisper 'small' model into HF_HOME so it's present at boot
# (no runtime download). Doubles as a build-time smoke test of the CPU int8 stack.
RUN /app/.venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

# App source + authored content + migrations, then the built SPA.
COPY app ./app
COPY content ./content
COPY migrations ./migrations
COPY alembic.ini start.sh ./
COPY scripts ./scripts
COPY --from=web /web/dist ./web/dist
RUN chmod +x start.sh scripts/docker-entrypoint.sh

EXPOSE 9000
# Entrypoint runs migrations + content sync, then serves (no --reload).
CMD ["./scripts/docker-entrypoint.sh"]
