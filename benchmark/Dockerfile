FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="x-bookmarks-library ONNX benchmark"
LABEL x-bookmarks-library.role="ephemeral-benchmark"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/models/huggingface \
    FASTEMBED_CACHE_PATH=/models/fastembed

RUN pip install --no-cache-dir "fastembed==0.7.3" "psutil==7.1.0"

WORKDIR /benchmark
COPY benchmark_model.py /benchmark/benchmark_model.py

USER 1000:1000
ENTRYPOINT ["python", "/benchmark/benchmark_model.py"]
