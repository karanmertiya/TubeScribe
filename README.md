# 📺 TubeScribe

> Paste a YouTube URL. Get comprehensive, beautifully typeset PDF notes — delivered instantly.

[![CI](https://github.com/karanmertiya/TubeScribe/actions/workflows/ci.yml/badge.svg)](https://github.com/karanmertiya/TubeScribe/actions)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Live demo →** [https://tubescribe-production.up.railway.app](https://tubescribe-production.up.railway.app/)

---

## What it does

1. Resolves a YouTube video or full playlist via `yt-dlp`
2. Downloads auto-generated English subtitles (VTT), deduplicates caption lines
3. Chunks the transcript into ~700-word segments
4. Sends each chunk to **Gemini 2.5 Flash** or **Groq Llama 3.3 70B** with a structured note-taking prompt
5. Renders the resulting Markdown into a typeset PDF (Source Serif 4, JetBrains Mono, WeasyPrint)
6. For playlists: builds an indexed table-of-contents cover page and merges all PDFs
7. Delivers to the developer via Telegram, or to users as a direct browser download

Progress streams in real-time via Server-Sent Events.

---

## Two modes

### 🔐 Developer mode
Sign in with a password. TubeScribe uses its own server-side API keys. Every result goes straight to your Telegram. The bot also accepts `/topdf <markdown>` — paste any Markdown into your Telegram chat and get a PDF back immediately. This feature is private and not exposed in the public UI.

### 👤 User mode
No account needed. Users supply their own Gemini or Groq API key in Settings (stored only in browser session memory — never sent to the server except in the request body, never logged). On completion, the PDF downloads directly to their browser.

---

## Tech stack

| Layer | Choice | Why |
|-------|--------|-----|
| Web framework | **FastAPI** | Async, SSE streaming, auto OpenAPI docs |
| LLM (primary) | **Gemini 2.5 Flash** | Best quality/speed for note extraction |
| LLM (alt) | **Groq Llama 3.3 70B** | Free-tier, near-instant inference |
| YouTube | **yt-dlp** | Best-in-class subtitle extraction |
| PDF rendering | **WeasyPrint** | True HTML/CSS → PDF, not canvas screenshots |
| PDF merging | **pypdf** | Lightweight, no Java |
| Markdown | **markdown2** | Tables, fenced code, footnotes |
| Auth | **HMAC signed cookie** | Stateless — no database required |
| PDF delivery (user) | **base64 in SSE** | No storage — browser downloads from event payload |
| Analytics | **SQLite** | Self-contained, no external service |
| Delivery | **Telegram Bot API** | Free, instant, 50 MB file support |
| Container | **Docker 3-stage build** | Fonts baked in; identical rendering locally and in prod |
| Deploy | **Railway + Docker** | Reads `railway.json`, auto-deploys on every push to `main` |

---

## Project structure

```
TubeScribe/
├── main.py                     # FastAPI app + routes (~270 lines)
├── backend/
│   ├── auth.py                 # Signed session cookie (no DB)
│   ├── analytics.py            # SQLite event counter
│   ├── pipeline.py             # SSE orchestration (dev vs user routing)
│   ├── llm/
│   │   ├── config.py           # LLMConfig — per-request, stateless
│   │   ├── gemini.py           # Gemini 2.5 Flash provider
│   │   └── groq.py             # Groq provider with retry + back-off
│   ├── youtube/
│   │   ├── transcript.py       # VTT download, dedup, chunking
│   │   └── playlist.py         # Playlist → [{url, title}]
│   ├── pdf/
│   │   ├── renderer.py         # Markdown → WeasyPrint PDF (offline fonts)
│   │   └── merger.py           # Index page + PDF merge
│   └── telegram/
│       ├── sender.py           # send_message / send_document
│       └── bot.py              # /topdf webhook handler (dev only, private)
├── frontend/
│   └── index.html              # Single-file SPA — dev + user mode
├── .github/
│   └── workflows/
│       └── ci.yml              # Lint + Docker build + smoke test
├── Dockerfile                  # 3-stage: builder → fonts → runtime
├── docker-compose.yml          # Local dev with persistent analytics volume
├── railway.json                # Railway deploy config (Docker builder)
├── requirements.txt
├── .env.example
├── .gitignore
├── .dockerignore
└── LICENSE
```

---

## Deployment

### Why Docker?
WeasyPrint depends on native system libraries (libpango, cairo, ffmpeg) whose exact versions affect font rendering. Docker locks everything so a PDF looks identical locally, in CI, and in production. The image also downloads fonts at build time — zero outbound HTTP calls during rendering.

### Local development
```bash
git clone https://github.com/karanmertiya/TubeScribe.git
cd TubeScribe
cp .env.example .env    # fill in your values

docker compose up --build
# → http://localhost:8000
```
The analytics DB is persisted in a named Docker volume (`tubescribe-data`) and survives container restarts.

### Railway (free tier, auto-deploy)
1. Fork this repo
2. [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Railway reads `railway.json` → uses the `Dockerfile` automatically
4. Set env vars in the Railway dashboard (see below)
5. Every `git push main` → Railway rebuilds and redeploys

**Required env vars:**
```
ADMIN_PASSWORD      your developer password
SESSION_SECRET      python -c "import secrets; print(secrets.token_hex(32))"
GEMINI_API_KEY      aistudio.google.com/apikey
TELEGRAM_BOT_TOKEN  @BotFather → /newbot
TELEGRAM_CHAT_ID    message @userinfobot
BASE_URL            https://your-app.railway.app
HTTPS               true
```

### Register the Telegram webhook (one-time, after deploy)
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-app.railway.app/webhook/telegram"
```

---

## API reference

Full interactive docs at `/docs`. Key endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Frontend |
| `/health` | GET | Service status + LLM/TG readiness |
| `/stats` | GET | Public usage counters |
| `/auth/login` | POST | Dev login `{"password":"…"}` |
| `/auth/logout` | POST | Clear session cookie |
| `/auth/me` | GET | Current mode + server config |
| `/process-playlist` | POST | Full pipeline, SSE stream |
| `/stream-notes` | POST | Single video, SSE markdown chunks |
| `/markdown-to-pdf` | POST | Markdown → PDF download |
| `/default-prompt` | GET | Default LLM system prompt |

---

## Analytics

`GET /stats` returns live counters — safe to embed in a portfolio or README badge:

```json
{
  "pdfs_generated":     142,
  "videos_processed":   389,
  "distinct_users":      47,
  "daily_active_users":   8
}
```

No PII is stored. Sessions are tracked as one-way SHA-256 hashes.

---

## License

MIT © Karan Singh Mertiya — see [LICENSE](LICENSE).
