# Deploying The Librarian

**Live:** http://158.158.120.189, on an Azure VM (Ubuntu 24.04, 2 vCPUs, 15 GB RAM), deployed on 4 Nov 2026 with the
"Any Linux VM" steps below. Answers take about 2-4 s there.

**Hugging Face Spaces now needs a paid plan.** Creating a Docker Space returned *402 Payment Required: hosting Gradio
and Docker Spaces on free cpu-basic requires a PRO subscription* (4 Nov 2026). The Hugging Face steps below still work
with HF PRO.

## Any Linux VM (what is deployed)

The service needs about 1.5-2 GB of RAM (the reranker) and port 80 open (Azure: an inbound rule on TCP 80 in the VM's
network security group).

```bash
# on the VM (Ubuntu), as the admin user
sudo apt-get install -y python3-venv python3-pip git
git clone https://github.com/dhfra21/ai-engineering.git && cd ai-engineering/project2-librarian
python3 -m venv .venv && .venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu   && .venv/bin/pip install -r requirements.txt
# .env with OPENAI_API_KEY and ADMIN_TOKEN (chmod 600), copied over scp, never committed
# index: copy data/index/article-oai/{embeddings.npy,meta.json} from a machine that has it, then rebuild the rest
# (reuses the embeddings when the chunk hash matches, so it costs nothing); without them it embeds for $0.14
.venv/bin/python -m src.index article-oai
sudo cp deploy/librarian.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now librarian
curl localhost/health
```

`deploy/librarian.service` runs uvicorn on port 80 as the normal user, restarts it if it stops, and starts it at
boot. It uses the Week 8 defaults from `src/service.py` (10 rerank candidates, no score threshold). To update the
VM after a push: `git pull && sudo systemctl restart librarian`. Logs: `journalctl -u librarian`; requests and
feedback in `~/librarian-logs/`, also downloadable with `/admin/export` (step 5 below).

## Hugging Face Spaces (needs HF PRO)

Needs an account on huggingface.co **with PRO**. The Space runs the container in `../Dockerfile` on a
CPU machine (16 GB RAM, enough for the reranker). The key stays a secret; it is never in the repo.

1. **Create the Space.** huggingface.co/new-space → name `librarian` → SDK **Docker** → *Blank* →
   hardware *CPU basic (free)* → visibility *Public* (so the instructor can open the URL) → Create.
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
5. **Feedback (optional; the team decided not to run a classmate round).** The page has thumbs up/down. If anyone
   uses it, download what they sent with:
   ```bash
   curl -H "Authorization: Bearer $ADMIN_TOKEN" "https://<your-user>-librarian.hf.space/admin/export?what=feedback" > feedback.jsonl
   curl -H "Authorization: Bearer $ADMIN_TOKEN" "https://<your-user>-librarian.hf.space/admin/export?what=requests" > requests.jsonl
   ```
   Logs live inside the container and are lost when the Space rebuilds or restarts, so export them regularly.
6. **Cost.** Each question costs a fraction of a cent (see the cost model); set a spending limit on the key's
   OpenAI project before sharing the URL widely.

Any other Docker host works the same way: `docker build --secret id=OPENAI_API_KEY,env=OPENAI_API_KEY -t librarian .`
then `docker run -p 7860:7860 -e OPENAI_API_KEY -e ADMIN_TOKEN librarian`.
