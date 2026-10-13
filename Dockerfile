# syntax=docker/dockerfile:1

# =============================================================================
# HAUdemicCheck - application image
#
# Packages the EXISTING Flask application without changing any application
# code. Dependencies are installed at build time (not at container start, so
# run.py is not used). NLTK resources are pre-fetched. The app is served by
# Gunicorn through the existing entry point `app:app`
# (app/__init__.py -> from app.frontend.main import app).
#
# Flask debug mode is NOT enabled in this image.
# =============================================================================

FROM python:3.11-slim

# Keep Python output/caches predictable and pin NLTK data to a default search
# path. PORT defaults to 5000 and is overridable at run time.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    NLTK_DATA=/usr/local/share/nltk_data \
    PORT=5000

# The application builds all of its paths from the source tree location
# (Path(__file__).resolve()), except loader.py which writes the relative path
# "logs/system.log". WORKDIR must therefore be the project root inside the
# image so that relative "logs/" resolves correctly.
WORKDIR /app

# -----------------------------------------------------------------------------
# Python dependencies - installed once, at build time.
# -----------------------------------------------------------------------------
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------------------------------------
# NLTK resources used by the application.
#
#   app/nlp/preprocessing.py -> punkt, punkt_tab, stopwords
#   app/nlp/similarity.py    -> punkt, punkt_tab
#
# Downloading them here means container startup no longer depends on fetching
# them from the network at import time.
# -----------------------------------------------------------------------------
RUN python -m nltk.downloader -d "${NLTK_DATA}" punkt punkt_tab stopwords

# -----------------------------------------------------------------------------
# Application source, including the local storage tree (corpus/, runtime_cache/,
# logs/, upload staging). See .dockerignore for why those are kept.
# -----------------------------------------------------------------------------
COPY . .

# Ensure every directory the application writes to exists. `logs/` in
# particular must exist before `app` is imported, because app/nlp/loader.py
# configures a file logger on "logs/system.log" at import time.
RUN mkdir -p \
        logs \
        corpus/promoted \
        corpus/processed \
        corpus/review \
        runtime_cache/corpus/promoted \
        runtime_cache/corpus/processed \
        app/static/file \
        app/utils/txtFileUpload

EXPOSE 5000

# -----------------------------------------------------------------------------
# Run the existing app with Gunicorn.
#
#   app:app          - existing WSGI entry point (no code changes)
#   0.0.0.0          - reachable from outside the container
#   ${PORT:-5000}    - configurable port, defaults to 5000
#   --workers 1      - preserves the in-memory, per-session RESULTS_STORE used
#                      by the /results and /review flow; multiple worker
#                      processes would fragment that session state
#   --threads 4      - serve concurrent requests within the single worker
#   --timeout 600    - corpus-wide similarity detection can run long; the
#                      Gunicorn default (30s) would kill valid requests
# -----------------------------------------------------------------------------
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 600 --graceful-timeout 30 --access-logfile - --error-logfile - app:app"]
