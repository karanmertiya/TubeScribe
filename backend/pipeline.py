"""
Pipeline orchestration — yields SSE events.
Imports from all backend packages; nothing else should import from here
except main.py routes.
"""
import base64
import datetime
import hashlib
import json
import logging
import os
import tempfile
import time
from typing import AsyncGenerator

from backend import analytics
from backend.llm import LLMConfig, call_llm
from backend.llm import gemini as gemini_mod
from backend.llm.config import LLMConfig as _LLMConfig
from backend.pdf import to_pdf, build_index, merge
from backend.telegram import send_document
from backend.youtube import extract, chunk, resolve

log         = logging.getLogger("tubescribe.pipeline")
CHUNK_WORDS = int(os.getenv("CHUNK_WORDS", "700"))


def _sse(event_type: str, msg: str, **extra) -> str:
    return f"data: {json.dumps({'type': event_type, 'msg': msg, **extra})}\n\n"


def _session_hash(token: str) -> str:
    """One-way hash of session token — no PII stored."""
    return hashlib.sha256(token.encode()).hexdigest()[:16]


async def run_playlist(
    url:        str,
    llm:        LLMConfig,
    dev_mode:   bool,
    session_id: str = "",
) -> AsyncGenerator[str, None]:
    """
    Full playlist pipeline with real-time SSE events.

    Dev mode  → merged PDF sent to developer's Telegram.
    User mode → SSE `done` event carries the merged PDF as base64 for browser download.
    """
    mode = "dev" if dev_mode else "user"

    # ── 1. Resolve playlist ────────────────────────────────────────
    yield _sse("progress", "🔍 Resolving playlist…", step="resolve")
    try:
        entries = resolve(url)
    except Exception as exc:
        yield _sse("error", f"Could not fetch playlist: {exc}")
        return

    total          = len(entries)
    playlist_title = f"YouTube Notes ({total} video{'s' if total > 1 else ''})"
    yield _sse("progress", f"📋 Found {total} video{'s' if total > 1 else ''}", total=total)

    all_pdfs:    list[bytes] = []
    done_titles: list[str]  = []

    # ── 2. Per-video processing ────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        for idx, entry in enumerate(entries, 1):
            vurl, vtitle = entry["url"], entry["title"]
            yield _sse("progress", f"🎬 [{idx}/{total}] {vtitle}",
                       step="video", index=idx, total=total)

            # Transcript
            try:
                _, transcript = extract(vurl, tmp)
            except Exception as exc:
                yield _sse("progress", f"  ⏭️ Skipped — {exc}", step="skip", index=idx)
                continue

            chunks = chunk(transcript, CHUNK_WORDS)
            yield _sse("progress",
                       f"  📝 {len(transcript.split()):,} words → {len(chunks)} chunk{'s' if len(chunks)>1 else ''}",
                       step="transcript", index=idx)

            analytics.record("video_processed", mode=mode, session=_session_hash(session_id), provider=llm.provider)

            # LLM notes
            full_md = f"# {vtitle}\n\n"
            for ci, c in enumerate(chunks, 1):
                yield _sse("progress", f"  🤖 Chunk {ci}/{len(chunks)}…",
                           step="llm", index=idx, chunk=ci, chunks=len(chunks))
                full_md += call_llm(llm, c) + "\n\n"
                if len(chunks) > 1:
                    time.sleep(0.4)

            # Render PDF
            yield _sse("progress", "  📄 Rendering PDF…", step="pdf", index=idx)
            try:
                pdf = to_pdf(vtitle, full_md, llm.label)
            except Exception as exc:
                yield _sse("progress", f"  ⚠️ PDF render failed: {exc}", step="pdf_error", index=idx)
                continue

            all_pdfs.append(pdf)
            done_titles.append(vtitle)
            analytics.record("pdf_generated", mode=mode, session=_session_hash(session_id), provider=llm.provider)

            yield _sse("video_done", f"  ✅ {vtitle}",
                       step="video_done", index=idx, total=total, done=len(done_titles))

    if not all_pdfs:
        yield _sse("error", "❌ No PDFs generated — all videos lacked English transcripts.")
        return

    # ── 3. Merge ───────────────────────────────────────────────────
    yield _sse("progress", f"📚 Merging {len(all_pdfs)} PDF(s)…", step="merge")
    try:
        merged = merge([build_index(playlist_title, done_titles)] + all_pdfs)
    except Exception as exc:
        yield _sse("error", f"PDF merge failed: {exc}")
        return

    size_mb  = len(merged) / (1024 * 1024)
    ts       = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"tubescribe_{ts}.pdf"

    # ── 4. Deliver ─────────────────────────────────────────────────
    if dev_mode:
        yield _sse("progress", f"📤 Sending to Telegram ({size_mb:.1f} MB)…", step="telegram")
        caption = (
            f"📒 <b>YouTube Notes</b>\n{playlist_title}\n"
            f"{len(done_titles)} videos · {size_mb:.1f} MB · {llm.label}"
        )
        send_document(caption, merged, filename)
        yield _sse("done",
                   f"🎉 {len(done_titles)} notes merged & sent to Telegram!",
                   step="done", filename=filename, size_mb=round(size_mb, 2),
                   videos_done=len(done_titles), videos_total=total)
    else:
        # Return PDF directly — browser triggers download from base64 in SSE payload
        pdf_b64 = base64.b64encode(merged).decode()
        yield _sse("done",
                   f"🎉 {len(done_titles)} notes ready — downloading…",
                   step="done", filename=filename, size_mb=round(size_mb, 2),
                   pdf_b64=pdf_b64,
                   videos_done=len(done_titles), videos_total=total)


async def run_single_stream(
    video_url:           str,
    llm:                 LLMConfig,
    dev_mode:            bool,
    session_id:          str = "",
    prefetched_title:     str | None = None,
    prefetched_transcript: str | None = None,
) -> AsyncGenerator[str, None]:
    """Single-video pipeline — streams markdown chunks as SSE.
    If prefetched_transcript is provided, skip the YouTube fetch entirely.
    """
    mode = "dev" if dev_mode else "user"

    with tempfile.TemporaryDirectory() as tmp:
        try:
            if prefetched_transcript:
                # Transcript fetched browser-side — skip YouTube entirely
                title      = prefetched_title or "Untitled Video"
                transcript = prefetched_transcript
                yield f"data: {json.dumps({'title': title})}\n\n"

                chunks = chunk(transcript, CHUNK_WORDS)
                yield f"data: {json.dumps({'total_chunks': len(chunks)})}\n\n"

                for i, c in enumerate(chunks, 1):
                    notes = call_llm(llm, c)
                    yield f"data: {json.dumps({'chunk': notes, 'chunk_index': i, 'total_chunks': len(chunks)})}\n\n"
                    if len(chunks) > 1:
                        time.sleep(0.2)

            else:
                # No pre-fetched transcript — try Cloudflare Worker first, then Gemini
                worker_url = os.getenv("YT_PROXY_WORKER", "").strip()
                title      = prefetched_title or None
                transcript_text = None

                if worker_url:
                    # Try the Worker — fast, free, preserves Gemini quota for notes
                    try:
                        from backend.youtube.transcript import extract as yt_extract
                        yield f"data: {json.dumps({'title': 'Fetching transcript via Worker…', 'status': 'fetching'})}\n\n"
                        title, transcript_text = yt_extract(video_url, "")
                        yield f"data: {json.dumps({'title': title})}\n\n"
                        log.info("Worker transcript OK for %s — using Groq for notes", video_url)
                    except Exception as exc:
                        log.warning("Worker transcript failed (%s): %s — falling back to Gemini", type(exc).__name__, exc)
                        yield f"data: {json.dumps({'type': 'log', 'msg': f'⚠ Worker failed: {exc} — using Gemini'})}\n\n"
                        transcript_text = None

                if transcript_text:
                    # Worker succeeded — use Groq/configured LLM for notes (faster, no Gemini quota)
                    chunks = chunk(transcript_text, CHUNK_WORDS)
                    yield f"data: {json.dumps({'total_chunks': len(chunks)})}\n\n"
                    for i, c in enumerate(chunks, 1):
                        notes = call_llm(llm, c)
                        yield f"data: {json.dumps({'chunk': notes, 'chunk_index': i, 'total_chunks': len(chunks)})}\n\n"
                        if len(chunks) > 1:
                            time.sleep(0.2)
                else:
                    # Gemini fallback — processes YouTube URL directly, no IP blocking
                    gemini_llm = _LLMConfig(
                        provider="gemini",
                        api_key=os.getenv("GEMINI_API_KEY", ""),
                        model="gemini-2.5-flash",
                        system_prompt=llm.system_prompt,
                    )
                    yield f"data: {json.dumps({'title': title or 'Processing via Gemini…', 'status': 'fetching'})}\n\n"
                    title, transcript, model_used = gemini_mod.get_transcript_from_url(gemini_llm, video_url)
                    yield f"data: {json.dumps({'title': title, 'model_used': model_used})}\n\n"

                    if transcript.startswith("__GEMINI_NOTES__\n"):
                        notes = transcript[len("__GEMINI_NOTES__\n"):]
                        yield f"data: {json.dumps({'total_chunks': 1})}\n\n"
                        yield f"data: {json.dumps({'chunk': notes, 'chunk_index': 1, 'total_chunks': 1})}\n\n"
                    else:
                        chunks = chunk(transcript, CHUNK_WORDS)
                        yield f"data: {json.dumps({'total_chunks': len(chunks)})}\n\n"
                        for i, ch in enumerate(chunks, 1):
                            notes = call_llm(llm, ch)
                            yield f"data: {json.dumps({'chunk': notes, 'chunk_index': i, 'total_chunks': len(chunks)})}\n\n"
                            if len(chunks) > 1:
                                time.sleep(0.2)

            analytics.record("video_processed", mode=mode,
                             session=_session_hash(session_id), provider=llm.provider)
            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as exc:
            msg = str(exc)
            # Strip raw API error blobs — show the clean message we wrote in gemini.py
            # If it's still a raw API error, give a generic helpful message
            if "{'error'" in msg or '"error"' in msg:
                msg = "Gemini API error — this video may be unavailable or restricted."
            yield f"data: {json.dumps({'error': msg})}\n\n"