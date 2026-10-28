ARG PYTHON_BASE
FROM ${PYTHON_BASE}
ARG UPSTREAM_COMMIT=c2859b23c9214e182c24d211714ae727e998be56
LABEL org.opencontainers.image.source="https://github.com/OxO-106/Papercut" \
      org.opencontainers.image.revision="${UPSTREAM_COMMIT}"
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    HOME=/cache XDG_CACHE_HOME=/cache HF_HOME=/cache/huggingface \
    HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 \
    OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
    PAPER_READER_LIBRARY=/library PAPERCUT_READER_ONLY=1 PAPERCUT_WORKER=1
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgl1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv==0.13.6
COPY deployment/requirements.lock /opt/requirements.lock
RUN uv pip sync --system --require-hashes --torch-backend cpu /opt/requirements.lock
WORKDIR /opt/papercut
COPY --chown=99:100 source/app ./app
COPY --chown=99:100 source/web ./web
COPY --chown=99:100 source/LICENSE ./LICENSE
USER 99:100
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=8)); assert r['ok'] and r['worker_alive']"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-proxy-headers"]
