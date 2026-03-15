"""
TubeScribe — v3
FastAPI entry point.  Routes only — all logic lives in backend/.

Run locally:
  uvicorn main:app --reload --port 8000

Deploy:
  Railway / Render / Fly.io — point to this file.
  Set env vars from .env.example in the platform dashboard.
"""
from __future__ import annotations
import datetime
import json
import logging
import os
import re

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.responses import Response as RawResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

from backend import analytics
from backend.auth import ADMIN_PASSWORD, is_dev, make_token, verify_token
from backend.llm import DEFAULT_SYSTEM_PROMPT, LLMConfig
from backend.pdf import to_pdf
from backend.pipeline import run_playlist, run_single_stream
from backend.telegram import handle_update, send_document
from fastapi.responses import StreamingResponse

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="TubeScribe",
    description="AI-powered YouTube → PDF notes — delivered to Telegram or browser download.",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.youtube.com",
        "https://youtube.com",
        "https://tube-scribe.up.railway.app",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Frontend ──────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def frontend():
    path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/html")
    return JSONResponse({"msg": "Frontend not found. API docs at /docs"})


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/login", tags=["Auth"])
async def login(request: Request, response: Response):
    """Dev login. POST {"password": "…"}."""
    import hmac
    body = await request.json()
    pw   = body.get("password", "")
    if not ADMIN_PASSWORD:
        return JSONResponse({"error": "Admin password not configured."}, status_code=503)
    if not hmac.compare_digest(pw, ADMIN_PASSWORD):
        return JSONResponse({"error": "Invalid password."}, status_code=401)
    token = make_token()
    response.set_cookie(
        key="session", value=token,
        httponly=True, secure=os.getenv("HTTPS", "false").lower() == "true",
        samesite="lax", max_age=86400 * 7,
    )
    return {"mode": "developer", "ok": True}


@app.post("/auth/logout", tags=["Auth"])
async def logout(response: Response):
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/auth/me", tags=["Auth"])
async def me(request: Request):
    dev = is_dev(request)
    from backend.llm.config import (DEFAULT_GEMINI_MODEL, DEFAULT_GROQ_MODEL,
                                    DEFAULT_PROVIDER, SERVER_GEMINI_KEY, SERVER_GROQ_KEY)
    return {
        "mode":           "developer" if dev else "user",
        "tg_configured":  bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID")),
        "llm_provider":   DEFAULT_PROVIDER,
        "llm_model":      DEFAULT_GEMINI_MODEL if DEFAULT_PROVIDER == "gemini" else DEFAULT_GROQ_MODEL,
        "gemini_ready":   bool(SERVER_GEMINI_KEY),
        "groq_ready":     bool(SERVER_GROQ_KEY),
    }


# ── System ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health():
    from backend.llm.config import DEFAULT_PROVIDER, SERVER_GEMINI_KEY, SERVER_GROQ_KEY
    return {
        "status":         "ok",
        "version":        "3.0.0",
        "llm_provider":   DEFAULT_PROVIDER,
        "gemini_ready":   bool(SERVER_GEMINI_KEY),
        "groq_ready":     bool(SERVER_GROQ_KEY),
        "telegram_ready": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
    }


@app.get("/stats", tags=["System"])
def stats():
    """Public stats — safe to embed in README badge."""
    return analytics.summary()


@app.get("/default-prompt", tags=["Utilities"])
def default_prompt():
    return {"prompt": DEFAULT_SYSTEM_PROMPT}


# ── Pipeline ──────────────────────────────────────────────────────────────────

def _resolve_llm_single(body: dict, dev: bool) -> tuple:
    """
    Single-video: dev mode uses server keys.
    User mode also uses server keys — single video is free for everyone.
    User-supplied api_key is accepted if provided (overrides server key).
    """
    if dev:
        llm = LLMConfig(system_prompt=body.get("system_prompt"))
    else:
        # User may optionally provide their own key; if not, fall back to server key
        llm = LLMConfig(
            provider=body.get("llm_provider"),
            model=body.get("llm_model"),
            api_key=body.get("api_key") or None,  # None → LLMConfig uses server key
            system_prompt=body.get("system_prompt"),
        )
        if err := llm.validate():
            return None, JSONResponse({"error": err}, status_code=400)
    return llm, None


def _resolve_llm_playlist(body: dict, dev: bool) -> tuple:
    """
    Playlist (Preview): dev mode uses server keys.
    User mode MUST supply their own API key — playlists are expensive and
    could exhaust server quota, so users bring their own key.
    """
    if dev:
        llm = LLMConfig(system_prompt=body.get("system_prompt"))
    else:
        user_key = (body.get("api_key") or "").strip()
        if not user_key:
            return None, JSONResponse(
                {"error": "Playlist generation requires your own API key. "
                          "Add it in ⚙️ Settings → API Key. "
                          "Get a free key at console.groq.com or aistudio.google.com/apikey"},
                status_code=400,
            )
        llm = LLMConfig(
            provider=body.get("llm_provider"),
            model=body.get("llm_model"),
            api_key=user_key,
            system_prompt=body.get("system_prompt"),
        )
        if err := llm.validate():
            return None, JSONResponse({"error": err}, status_code=400)
    return llm, None


@app.post("/process-playlist", tags=["Pipeline"])
async def process_playlist(request: Request):
    """
    Full playlist pipeline. Real-time SSE progress stream.

    **Dev mode** (session cookie): server keys, merged PDF → owner Telegram.

    **User mode**: supply `api_key`. On completion the `done` SSE event carries
    `pdf_b64` (base64-encoded PDF) — the frontend triggers a browser download directly.
    No server storage, no expiring links.

    ```json
    {
      "url":           "https://youtube.com/playlist?list=…",
      "llm_provider":  "gemini",
      "llm_model":     "gemini-2.5-flash",
      "api_key":       "…",
      "system_prompt": "…"
    }
    ```
    """
    body = await request.json()
    url  = (body.get("url") or "").strip()
    if not url:
        return JSONResponse({"error": "url is required"}, status_code=400)

    dev = is_dev(request)
    llm, err = _resolve_llm_playlist(body, dev)
    if err:
        return err

    session = request.cookies.get("session", "")
    return StreamingResponse(
        run_playlist(url, llm, dev, session),
        media_type="text/event-stream",
    )


@app.post("/stream-notes", tags=["Pipeline"])
async def stream_notes(request: Request):
    """Single-video SSE stream — returns markdown chunks in real-time."""
    body = await request.json()
    url  = (body.get("url") or "").strip()
    pre_title      = (body.get("title") or body.get("prefetched_title") or "").strip() or None
    pre_transcript = (body.get("transcript") or body.get("prefetched_transcript") or "").strip() or None

    if not url and not pre_transcript:
        return JSONResponse({"error": "url is required"}, status_code=400)
    if not url:
        url = f"https://www.youtube.com/watch?v={body.get('video_id', '')}"

    dev = is_dev(request)
    llm, err = _resolve_llm_single(body, dev)
    if err:
        return err

    session = request.cookies.get("session", "")
    return StreamingResponse(
        run_single_stream(url, llm, dev, session,
                          prefetched_title=pre_title,
                          prefetched_transcript=pre_transcript),
        media_type="text/event-stream",
    )


# ── Utilities ─────────────────────────────────────────────────────────────────

@app.post("/markdown-to-pdf", tags=["Utilities"])
async def markdown_to_pdf(request: Request):
    """
    Convert Markdown → styled PDF.

    - **Dev mode**: auto-sends to owner Telegram + returns file.
    - **User mode**: returns file. If `tg_token` + `tg_chat` are set,
      sends a download link to user's Telegram as well.
    """
    body  = await request.json()
    title = (body.get("title") or "Notes").strip()
    md    = (body.get("markdown") or "").strip()
    if not md:
        return JSONResponse({"error": "markdown field is required"}, status_code=400)

    dev = is_dev(request)

    try:
        pdf_bytes = to_pdf(title, md)
    except Exception as exc:
        return JSONResponse({"error": f"PDF generation failed: {exc}"}, status_code=500)

    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', title[:40])}_{ts}.pdf"

    analytics.record("pdf_generated", mode="dev" if dev else "user")

    if dev:
        send_document(f"📄 {title}", pdf_bytes, filename)

    return RawResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ── Bookmarklet receiver ───────────────────────────────────────────────────────

@app.post("/from-browser", tags=["Pipeline"], include_in_schema=False)
async def from_browser(request: Request):
    """
    Receives transcript POSTed by the TubeScribe bookmarklet.
    Renders the main UI with transcript pre-loaded so processing starts immediately.
    """
    form        = await request.form()
    title       = (form.get("title") or "Untitled Video").strip()
    video_id    = (form.get("video_id") or "").strip()
    transcript  = (form.get("transcript") or "").strip()

    if not transcript:
        return JSONResponse({"error": "No transcript received"}, status_code=400)

    try:
        html_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
        with open(html_path, encoding="utf-8") as f:
            page = f.read()

        inject = f"""
<script>
window._tubescribeAutostart = {{
  title: {json.dumps(title)},
  videoId: {json.dumps(video_id)},
  transcript: {json.dumps(transcript)}
}};
</script>"""

        page = page.replace("</head>", inject + "\n</head>", 1)
        return RawResponse(content=page.encode(), media_type="text/html")
    except Exception as exc:
        import traceback
        return JSONResponse({"error": str(exc), "trace": traceback.format_exc()}, status_code=500)


@app.post("/playlist-zip", tags=["Pipeline"], include_in_schema=False)
async def playlist_zip(request: Request):
    """
    Receives a list of {title, markdown} objects, generates PDFs for each,
    and returns them as a ZIP file.
    """
    import zipfile
    import io
    body = await request.json()
    playlist_title = (body.get("playlist_title") or "playlist").strip()
    videos = body.get("videos") or []

    if not videos:
        return JSONResponse({"error": "No videos provided"}, status_code=400)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, v in enumerate(videos, 1):
            title    = (v.get("title") or f"Video {i}").strip()
            markdown = (v.get("markdown") or "").strip()
            if not markdown:
                continue
            try:
                pdf_bytes = to_pdf(title, markdown)
                safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", title[:60])
                zf.writestr(f"{i:02d}_{safe_name}.pdf", pdf_bytes)
            except Exception as exc:
                log.warning("PDF failed for '%s': %s", title, exc)

    zip_buf.seek(0)
    safe_playlist = re.sub(r"[^a-zA-Z0-9_-]", "_", playlist_title[:60])
    return RawResponse(
        content=zip_buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_playlist}.zip"'},
    )



async def debug_paths():
    import glob
    base = os.path.dirname(__file__)
    frontend = os.path.join(base, "frontend")
    return {
        "__file__": __file__,
        "base": base,
        "frontend_dir_exists": os.path.exists(frontend),
        "frontend_files": glob.glob(os.path.join(frontend, "*")) if os.path.exists(frontend) else [],
        "setup_exists": os.path.exists(os.path.join(frontend, "setup.html")),
    }

@app.get("/bookmarklet.js", include_in_schema=False)
async def bookmarklet_script():
    """Serves the sidebar bookmarklet — update this file, all users get it instantly."""
    path = os.path.join(os.path.dirname(__file__), "frontend", "bookmarklet.js")
    if os.path.exists(path):
        return FileResponse(path, media_type="application/javascript",
                            headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return JSONResponse({"error": "Bookmarklet not found"}, status_code=404)



async def setup_page(request: Request):
    """Bookmarklet setup page."""
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "setup.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return JSONResponse({"error": "Setup page not found"}, status_code=404)


# ── Telegram Webhook (developer's bot only) ───────────────────────────────────

@app.post("/webhook/telegram", include_in_schema=False)
async def telegram_webhook(request: Request):
    """
    Telegram bot webhook. Register once:
      curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=<BASE_URL>/webhook/telegram"

    Handles /topdf command (developer only).
    """
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        return JSONResponse({"error": "Telegram not configured."}, status_code=503)
    try:
        update = await request.json()
        await handle_update(update)
    except Exception as exc:
        logging.getLogger(__name__).error("Webhook error: %s", exc)
    return {"ok": True}
