# The Librarian as a container (Hugging Face Spaces "Docker" SDK, or any Docker host).
# Build:  docker build --secret id=OPENAI_API_KEY,env=OPENAI_API_KEY -t librarian .
# Run:    docker run -p 7860:7860 -e OPENAI_API_KEY=... -e ADMIN_TOKEN=... librarian
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /app
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=user src ./src
COPY --chown=user data/corpus/txt ./data/corpus/txt
COPY --chown=user data/corpus/fr ./data/corpus/fr
COPY --chown=user scripts/start.sh ./scripts/start.sh
RUN chown user /app && mkdir -p data/index logs && chown -R user data/index logs
USER user
ENV HF_HOME=/home/user/.cache/huggingface PORT=7860 INDEX_NAME=article-oai
# bake the reranker model into the image so cold starts do not download it
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1')"
# build the index at image build time if the key is available as a build secret (about 3 minutes, $0.14);
# otherwise scripts/start.sh builds it on first boot
RUN --mount=type=secret,id=OPENAI_API_KEY,uid=1000 \
    if [ -f /run/secrets/OPENAI_API_KEY ]; then OPENAI_API_KEY="$(cat /run/secrets/OPENAI_API_KEY)" python -m src.index "$INDEX_NAME"; else echo "no build secret: index will be built at first start"; fi
EXPOSE 7860
CMD ["sh", "scripts/start.sh"]
