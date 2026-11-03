#!/usr/bin/env bash
# Download the prebuilt embeddings from a GitHub release and finish the index locally.
#   scripts/fetch_index.sh <release-asset-url> <index-name> [<index-name> ...]
# e.g. scripts/fetch_index.sh https://github.com/dhfra21/ai-engineering/releases/download/index-v1/librarian-index.tar.gz article-oai
# After extracting, `python -m src.index <name>` rebuilds chunks/tokens and checks that the
# embeddings match them (hash); it only re-embeds if they do not.
set -euo pipefail
cd "$(dirname "$0")/.."
url="$1"; shift
mkdir -p dist
curl -L --fail -o dist/librarian-index.tar.gz "$url"
tar xzf dist/librarian-index.tar.gz
for name in "$@"; do .venv/bin/python -m src.index "$name"; done
