#!/bin/sh
# Container entry point: make sure the index exists, then serve.
set -e
if [ ! -f "data/index/${INDEX:-article-oai}/embeddings.npy" ]; then
  echo "index missing: building it now (needs OPENAI_API_KEY)"
  python -m src.index "${INDEX:-article-oai}"
fi
exec uvicorn src.service:app --host 0.0.0.0 --port "${PORT:-7860}"
