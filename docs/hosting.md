# Hosting (single VPS + Docker + Caddy)

The whole app runs as one container (FastAPI serving the built SPA) behind Caddy
(automatic HTTPS), with Ollama for local AI. SQLite + authored audio live on a data
volume. Sized for a closed group of friends — no cluster, no managed DB.

```
  Caddy :80/:443  --auto-TLS-->  app:9000 (FastAPI + web/dist)
                                 Ollama :11434 (local models)
  volume ./data  (tef.db + assets)   volume ollama (models)
```

## One-time setup on the box

1. **Provision** a VPS. Because AI runs on **Ollama**, size it for the model —
   **16 GB+ RAM (GPU ideal)**. (Without Ollama a 1–2 GB box is plenty; see below.)
2. **Install Docker** (Docker Engine + compose plugin).
3. **Clone + configure**:
   ```bash
   git clone <repo> && cd multilingual
   cp .env.example .env
   ```
   In `.env` set, at minimum:
   - `JWT_SECRET` — `openssl rand -hex 32`
   - `INVITE_CODES` — your own signup codes (comma-separated)
   - `SITE_ADDRESS` — your domain (e.g. `tef.example.com`) for HTTPS, or leave
     blank to serve plain HTTP on `:80`
   - Point the domain's DNS A record at the box before starting (Caddy needs it to
     issue the cert).
4. **Launch**:
   ```bash
   docker compose up -d --build
   docker compose exec ollama ollama pull llama3.1   # + any models in ai_routing.yaml
   ```
   On boot the app container runs migrations and syncs all content automatically
   (`scripts/docker-entrypoint.sh`), so the DB is ready with no manual step.

Visit `https://<SITE_ADDRESS>`, sign up with an invite code, and you're in.

## Redeploys

```bash
git pull && docker compose up -d --build
```
Migrations + content sync re-run on boot (idempotent), so content/schema updates
apply themselves.

## Backups (do this)

State is one SQLite file. Cron a nightly copy **off the box**:
```bash
0 3 * * *  cp /path/multilingual/data/tef.db /path/backups/tef-$(date +\%F).db
```
`data/assets/` (audio) is rebuildable from `content/` via `scripts/gen_audio.py`, so
`tef.db` is the only thing that's truly precious.

## Running without Ollama (cheap box)

Most of the app works with **no LLM**: lessons, SRS, comprehension, progress, exam
scoring. Only tutor drills / writing feedback / examiner need a model, and they
degrade to a clean 503 until one is configured. To run lean:

- Drop the `ollama` service (and `depends_on`) from `docker-compose.yml`, or
- Keep it and set `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` in `.env` to use a
  hosted model instead (see `app/config/ai_routing.yaml`).

## What's where

| Concern | File |
|---|---|
| Image (multi-stage: Node builds SPA → Python serves) | `Dockerfile` |
| Boot: migrate + sync content + serve | `scripts/docker-entrypoint.sh` |
| Stack: app + Ollama + Caddy | `docker-compose.yml` |
| Reverse proxy + TLS | `Caddyfile` |
| Secrets / config | `.env` (from `.env.example`) |
