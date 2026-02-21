FROM python:3.12-slim AS base

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2 && \
    curl -L --retry 3 --retry-delay 5 --max-time 300 \
      -o /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz \
      https://chroma-onnx-models.s3.amazonaws.com/all-MiniLM-L6-v2/onnx.tar.gz && \
    tar -xzf /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz \
      -C /root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/ && \
    echo "ONNX embedding model cached"

COPY . ./agent/

RUN mkdir -p /opt/agent/data/artifacts

EXPOSE 8100

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')"

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8100", "--log-level", "info"]
