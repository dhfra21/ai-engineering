# Deploying The Librarian (Hugging Face Spaces)

Needs an account on huggingface.co (free). The Space runs the container in `../Dockerfile` on a free
CPU machine (16 GB RAM, enough for the reranker). The key stays a secret; it is never in the repo.

1. **Create the Space.** huggingface.co/new-space → name `librarian` → SDK **Docker** → *Blank* →
   hardware *CPU basic (free)* → visibility *Public* (needed for classmates) → Create.
2. **Add secrets** (Space → Settings → *Variables and secrets* → *New secret*):
   - `OPENAI_API_KEY`: the course key. It is also used while the image builds, to create the index.
   - `ADMIN_TOKEN`: a long random string of your own. It protects `/admin/export`.
3. **Push the code.** From the repo root:
   ```bash
   git clone https://huggingface.co/spaces/<your-user>/librarian /tmp/space && cd /tmp/space
   cp -r <repo>/project2-librarian/{Dockerfile,.dockerignore,requirements.txt,src,scripts} .
   mkdir -p data/corpus && cp -r <repo>/project2-librarian/data/corpus/{txt,fr} data/corpus/
   cp <repo>/project2-librarian/deploy/hf_space_README.md README.md
   git add . && git commit -m "Deploy The Librarian" && git push      # password = a HF access token with write role
   ```
4. **Wait for the build** (Space page → *Logs*; about 10 minutes the first time). The URL is
   `https://<your-user>-librarian.hf.space`. Check `/health`, then ask a question on the home page.
5. **Collect feedback.** Share the URL with classmates (the page has thumbs up/down). Download what they
   sent with:
   ```bash
   curl -H "Authorization: Bearer $ADMIN_TOKEN" "https://<your-user>-librarian.hf.space/admin/export?what=feedback" > feedback.jsonl
   curl -H "Authorization: Bearer $ADMIN_TOKEN" "https://<your-user>-librarian.hf.space/admin/export?what=requests" > requests.jsonl
   ```
   Logs live inside the container and are lost when the Space rebuilds or restarts, so export them regularly.
6. **Cost.** Each question costs a fraction of a cent (see the cost model); set a spending limit on the key's
   OpenAI project before sharing the URL widely.

Any other Docker host works the same way: `docker build --secret id=OPENAI_API_KEY,env=OPENAI_API_KEY -t librarian .`
then `docker run -p 7860:7860 -e OPENAI_API_KEY -e ADMIN_TOKEN librarian`.
