FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HELPME_ROOT=/app \
    HELPME_DATA_DIR=/app/.data

WORKDIR /app

ARG APP_VERSION=unknown
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="helpme.green" \
      org.opencontainers.image.description="Circular-economy AI-backed R&D assistant" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/bnelabs/helpme.green"

COPY pyproject.toml ./
COPY src ./src
COPY static ./static
COPY assets ./assets
COPY knowledge ./knowledge
COPY skills ./skills
RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin helpme \
    && mkdir -p /app/.data \
    && chown -R helpme:helpme /app
USER helpme

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"

CMD ["python", "-m", "helpme_green", "--serve", "--host", "0.0.0.0", "--port", "8080"]
