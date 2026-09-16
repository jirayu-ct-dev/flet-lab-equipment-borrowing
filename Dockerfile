FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_SEED_RENDER_DEMO=1

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docs/cs66.md ./docs/cs66.md
COPY main.py ./

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 10000

# Render supplies PORT at runtime; 8550 keeps the same behavior for local Docker use.
CMD ["sh", "-c", "flet run --web --host '*' --port \"${PORT:-8550}\" main.py"]
