#!/usr/bin/env bash
# Pack the expensive part of one or more indexes (embeddings.npy + meta.json) for a GitHub release.
#   scripts/pack_index.sh article-oai [article ...]     -> dist/librarian-index.tar.gz
# chunks.jsonl / tokens.jsonl are not packed: they are rebuilt from the corpus in under a minute.
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 <index-name> [<index-name> ...]"; exit 1; }
mkdir -p dist
files=()
for name in "$@"; do
  for f in embeddings.npy meta.json; do
    [ -f "data/index/$name/$f" ] || { echo "missing data/index/$name/$f"; exit 1; }
    files+=("data/index/$name/$f")
  done
done
tar czf dist/librarian-index.tar.gz "${files[@]}"
ls -lh dist/librarian-index.tar.gz
sha256sum dist/librarian-index.tar.gz
