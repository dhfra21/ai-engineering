# Hardware note

Fill this in after actually running `qwen2.5-coder:7b-instruct` locally.
`src/cost.py` reads the machine-readable copy of this info from
`results/hardware.json` — keep both in sync.

- **Machine:** _(CPU/GPU model, RAM/VRAM, OS)_
- **Serving stack:** Ollama _(version)_ — `ollama pull qwen2.5-coder:7b-instruct`
- **Quantization:** _(Ollama's default for this tag, or note if you pulled a specific quant)_
- **Measured throughput:** _(avg tokens/second across the 50 calls — printed by `python -m src.cost`)_
- **Hourly cost basis:** _(how you priced `cost_per_hour_usd` in hardware.json — e.g. a comparable
  cloud GPU instance's on-demand rate, or local electricity cost)_
- **Anything that slowed it down:** _(thermal throttling, other processes competing for the GPU, etc.)_
