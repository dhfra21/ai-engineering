# Hardware note

Machine-readable copy of this info lives in `results/hardware.json`,
which `src/cost.py` reads — keep both in sync.

- **Machine:** MSI Thin GF63 12UCX laptop — Intel Core i5-12450H (8C/12T),
  23.7 GB RAM, NVIDIA GeForce RTX 2050 with 4 GB VRAM, Windows 11 Pro.
- **Serving stack:** Ollama 0.34.2 — `ollama pull qwen2.5-coder:7b-instruct`,
  served over the local HTTP API at `localhost:11434` (`/api/generate`,
  `stream: false`, `temperature: 0`, `num_predict: 512`).
- **Quantization:** Ollama's default for this tag — Q4, ~4.7 GB on disk.
- **Measured throughput:** **3.6 tokens/second** average across the 50
  calls (from `eval_count / eval_duration` in each Ollama response;
  printed by `python -m src.cost`). Latency: p50 14,136 ms, p95 25,152 ms.
- **Hourly cost basis:** **$0.0144/hour**, electricity only, for a laptop
  we already own — 120 W sustained under inference load (estimated, not
  measured with a wall meter) at the STEG residential tariff of roughly
  0.36 TND/kWh ≈ USD 0.12/kWh. This **excludes hardware amortisation and
  our own time**; the report states that explicitly, because including
  either moves the break-even volume a lot. The amortised alternative
  would be (laptop price / expected lifetime hours) + electricity.
- **Anything that slowed it down:** yes, and it dominates the latency
  numbers. The Q4 model is ~4.7 GB against 4 GB of VRAM, so **Ollama
  offloads part of the model to CPU** — 3.6 tok/s is roughly an order of
  magnitude below what this model does when fully GPU-resident. The
  14 s p50 and the ~253 req/hour throughput ceiling in the report's
  section 6 are both consequences of that offload, not of the model
  itself. A GPU with 8 GB of VRAM would change the self-hosted column
  substantially, in both latency and cost per request.
