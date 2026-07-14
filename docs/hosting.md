# Hosting

The whole app runs as one container (FastAPI serving the built SPA) plus Ollama for
local AI. SQLite + authored audio live on a data volume. Sized for a closed group of
friends — no cluster, no managed DB.

Primary path below: a **Linux laptop with an NVIDIA GPU**, reached over **Tailscale**.
A public-domain (Caddy) alternative is at the end.

```
  Tailscale  --HTTPS-->  app 127.0.0.1:9000 (FastAPI + web/dist)
                         Ollama :11434 (GPU, local models)
  volume ./data (tef.db + assets)   volume ollama (models)
```

## Self-hosted laptop (NVIDIA + Tailscale)

### 1. Host prerequisites
- **Docker Engine** + compose plugin.
- **NVIDIA driver** (`nvidia-smi` works on the host).
- **NVIDIA Container Toolkit** so containers can use the GPU — install per NVIDIA's
  guide, then wire it into Docker:
  ```bash
  sudo nvidia-ctk runtime configure --runtime=docker
  sudo systemctl restart docker
  # verify the GPU is visible inside a container:
  docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
  ```
- **Tailscale** (`curl -fsSL https://tailscale.com/install.sh | sh`), then
  `sudo tailscale up`. In the admin console enable **MagicDNS** and **HTTPS
  certificates** (Settings → Features).

### 2. Configure + launch
```bash
git clone <repo> && cd multilingual
cp .env.example .env         # set JWT_SECRET (openssl rand -hex 32) and INVITE_CODES
                             # leave SITE_ADDRESS blank — Tailscale handles TLS

docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose exec ollama ollama pull llama3.1   # + any model in ai_routing.yaml
```
On boot the app container runs migrations and syncs all content automatically
(`scripts/docker-entrypoint.sh`), so the DB is ready with no manual step. It listens
on **127.0.0.1:9000** (loopback only — not exposed to the LAN).

Confirm the GPU is actually in use:
```bash
docker compose exec ollama ollama ps    # shows "100% GPU" for a loaded model
```

### 3. Expose it over Tailscale (automatic HTTPS)
```bash
sudo tailscale serve --bg 9000
tailscale serve status                  # prints the https://<name>.ts.net URL
```
Tailscale terminates TLS and proxies to `127.0.0.1:9000`, with certs it renews
itself — no Caddy, no port-forwarding, nothing exposed to the public internet.
Friends reach `https://<your-laptop>.<tailnet>.ts.net` once they're on your tailnet
(invite them, or **Share** this machine from the admin console).

> HTTPS matters if you later enable the speech feature — browsers only allow
> microphone access on secure origins.

### 4. Keep the laptop serving (don't sleep on lid close)
```bash
# /etc/systemd/logind.conf
HandleLidSwitch=ignore
HandleLidSwitchExternalPower=ignore
```
then `sudo systemctl restart systemd-logind`. (Or keep it on a desk on AC power.)

## Redeploys
```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```
Migrations + content sync re-run on boot (idempotent), so content/schema updates
apply themselves.

## Backups (do this)
State is one SQLite file. Cron a nightly copy **off the laptop**:
```bash
0 3 * * *  cp /path/multilingual/data/tef.db /path/backups/tef-$(date +\%F).db
```
`data/assets/` (audio) is rebuildable from `content/` via `scripts/gen_audio.py`, so
`tef.db` is the only thing that's truly precious.

## Running the model on CPU (no/weak GPU)
Omit the GPU override — `docker compose up -d --build` runs Ollama on CPU (slower).
Or skip Ollama entirely and set `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` in `.env`
to use a hosted model. Either way the non-AI features (lessons, SRS, comprehension,
progress, exam scoring) work regardless; only tutor/writing/examiner need a model and
they 503 cleanly until one is configured.

## Alternative: public domain + Caddy (VPS / port-forwarded)
If instead you have a domain and want a public URL, use the Caddy override for
automatic HTTPS:
```bash
# .env: SITE_ADDRESS=tef.example.com  (DNS A record -> the box first)
docker compose -f docker-compose.yml -f docker-compose.caddy.yml up -d --build
```

## What's where
| Concern | File |
|---|---|
| Image (multi-stage: Node builds SPA → Python serves) | `Dockerfile` |
| Boot: migrate + sync content + serve | `scripts/docker-entrypoint.sh` |
| Base stack: app + Ollama | `docker-compose.yml` |
| NVIDIA GPU override | `docker-compose.gpu.yml` |
| Caddy override (public domain) | `docker-compose.caddy.yml` + `Caddyfile` |
| Secrets / config | `.env` (from `.env.example`) |
