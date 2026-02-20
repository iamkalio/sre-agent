FROM python:3.12-slim AS base

WORKDIR /opt

RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the ChromaDB ONNX embedding model so it's baked into the image
RUN python -c "\
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; \
ef = ONNXMiniLM_L6_V2(); \
ef(['warmup']); \
print('ONNX model cached successfully')"

COPY . ./agent/

RUN mkdir -p /opt/agent/data/chroma /opt/agent/data/artifacts

EXPOSE 8100

HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8100/health')"

CMD ["uvicorn", "agent.main:app", "--host", "0.0.0.0", "--port", "8100", "--log-level", "info"]
