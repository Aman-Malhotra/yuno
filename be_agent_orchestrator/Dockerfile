FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    # mem0's HuggingFace embedder caches the MiniLM model here. Pinning
    # the path so the bake step and runtime use the same location.
    HF_HOME=/root/.cache/huggingface

# build-essential — psycopg[binary] ships wheels, but a couple of mem0's
# transitive deps build C extensions on first install. Keeping the layer
# minimal so the image doesn't balloon.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Pre-warm the sentence-transformers model into the HF cache so the
# first memory call doesn't stall on a ~90MB download. Adds time + size
# to the build, but `docker compose up` becomes instant-on for memory.
RUN uv run python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

EXPOSE 3001

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3001"]
