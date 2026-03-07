# ══════════════════════════════════════════════════════════════════
# Stage 1 — Python dependency builder
# ══════════════════════════════════════════════════════════════════
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ══════════════════════════════════════════════════════════════════
# Stage 2 — Font downloader
# Downloads fonts ONCE at build time so the runtime image never
# makes outbound HTTP requests during PDF rendering.
# ══════════════════════════════════════════════════════════════════
FROM debian:bookworm-slim AS fonts

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /fonts

# Source Serif 4 — variable fonts from adobe-fonts/source-serif (official upstream)
# Confirmed paths: /VAR/SourceSerif4Variable-Roman.ttf and Italic variant
RUN curl -fsSL -o SourceSerif4.ttf \
    "https://github.com/adobe-fonts/source-serif/raw/release/VAR/SourceSerif4Variable-Roman.ttf"

RUN curl -fsSL -o SourceSerif4-Italic.ttf \
    "https://github.com/adobe-fonts/source-serif/raw/release/VAR/SourceSerif4Variable-Italic.ttf"

# JetBrains Mono
RUN curl -fsSL -o JetBrainsMono-Regular.ttf \
    "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-Regular.ttf"

RUN curl -fsSL -o JetBrainsMono-SemiBold.ttf \
    "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-SemiBold.ttf"


# ══════════════════════════════════════════════════════════════════
# Stage 3 — Runtime image
# ══════════════════════════════════════════════════════════════════
FROM python:3.11-slim

LABEL org.opencontainers.image.title="TubeScribe"
LABEL org.opencontainers.image.description="AI-powered YouTube to PDF notes pipeline"
LABEL org.opencontainers.image.source="https://github.com/karanmertiya/TubeScribe"

WORKDIR /app

# WeasyPrint needs: pango (text layout), cairo (rendering), gdk-pixbuf (images)
# yt-dlp needs:    ffmpeg (post-processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    fonts-liberation \
    fontconfig \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python packages from builder stage
COPY --from=builder /install /usr/local

# Fonts baked in — no runtime HTTP calls during PDF rendering
COPY --from=fonts /fonts/ /usr/local/share/fonts/tubescribe/
RUN fc-cache -f -v > /dev/null 2>&1

# Application code
COPY main.py              ./main.py
COPY backend/             ./backend/
COPY frontend/index.html  ./frontend/index.html

# Data directory for analytics DB (mount a volume here in prod)
RUN mkdir -p /data && chmod 777 /data

# Non-root user for security
RUN useradd -m -u 1001 appuser \
    && chown -R appuser:appuser /app /data
USER appuser

ENV DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --access-log --log-level info"]
