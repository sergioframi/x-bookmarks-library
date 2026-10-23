FROM python:3.12-slim-bookworm AS extension-builder
WORKDIR /source
COPY extension/xarchive /source/extension/xarchive
COPY scripts/sync-extension-release.py scripts/build-extension-package.py /source/scripts/
RUN python scripts/sync-extension-release.py && \
    python scripts/build-extension-package.py --destination /build/xarchive-connector.zip

FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.title="x-bookmarks-library" \
    org.opencontainers.image.description="Private, self-hosted X bookmark library"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PORT=8080 \
    HF_HOME=/app/models/huggingface FASTEMBED_CACHE_PATH=/app/models/fastembed
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN useradd --uid 1000 --create-home appuser && \
    mkdir -p /app/data /app/models /app/logs /app/imports /app/app/assets && \
    chown -R appuser:appuser /app
WORKDIR /app
COPY --chown=appuser:appuser app /app/app
COPY --chown=appuser:appuser manage.py /app/manage.py
COPY --from=extension-builder --chown=appuser:appuser /build/xarchive-connector.zip /app/app/assets/xarchive-connector.zip
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=15s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3).read()"
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8080","--workers","1","--no-access-log"]
