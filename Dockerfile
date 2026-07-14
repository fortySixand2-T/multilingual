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
RUN pip install --no-cache-dir uv

WORKDIR /app
# Dependency layer (cached until the lock changes). --no-install-project: install
# deps only; the app runs from the copied source below.
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-install-project

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
