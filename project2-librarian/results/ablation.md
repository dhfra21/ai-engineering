### main set (50 facts x 2 languages), chunking = article

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 87% | 92% | 93% | 97% | 0.898 | 96% | 90% | 66 ms | 96 ms |
| vector only | 73% | 88% | 91% | 95% | 0.812 | 94% | 88% | 152 ms | 168 ms |
| hybrid (RRF) | 83% | 90% | 93% | 98% | 0.874 | 96% | 90% | 159 ms | 179 ms |
| hybrid + reranker | 97% | 100% | 100% | 100% | 0.985 | 100% | 100% | 7.4 s | 7.9 s |

### main set (50 facts x 2 languages), chunking = fixed

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 78% | 89% | 95% | 98% | 0.846 | 94% | 96% | 53 ms | 77 ms |
| vector only | 59% | 77% | 91% | 97% | 0.715 | 92% | 90% | 148 ms | 168 ms |
| hybrid (RRF) | 70% | 91% | 94% | 99% | 0.804 | 96% | 92% | 151 ms | 171 ms |
| hybrid + reranker | 94% | 99% | 100% | 100% | 0.967 | 100% | 100% | 7.3 s | 9.5 s |

### main set (50 facts x 2 languages), chunking = article-oai

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 87% | 92% | 93% | 97% | 0.898 | 96% | 90% | 122 ms | 200 ms |
| vector only | 73% | 89% | 92% | 95% | 0.817 | 90% | 94% | 327 ms | 506 ms |
| hybrid (RRF) | 84% | 93% | 94% | 100% | 0.894 | 94% | 94% | 487 ms | 653 ms |
| hybrid + reranker | 97% | 100% | 100% | 100% | 0.983 | 100% | 100% | 9.1 s | 10.7 s |

### paraphrased set (25 facts x 2 languages), chunking = article

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 12% | 24% | 32% | 46% | 0.207 | 32% | 32% | 91 ms | 134 ms |
| vector only | 42% | 56% | 64% | 74% | 0.509 | 68% | 60% | 161 ms | 218 ms |
| hybrid (RRF) | 26% | 46% | 58% | 68% | 0.387 | 60% | 56% | 174 ms | 222 ms |
| hybrid + reranker | 52% | 66% | 74% | 76% | 0.599 | 72% | 76% | 8.6 s | 9.8 s |

### paraphrased set (25 facts x 2 languages), chunking = fixed

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 12% | 26% | 30% | 40% | 0.206 | 36% | 24% | 68 ms | 90 ms |
| vector only | 36% | 50% | 60% | 68% | 0.457 | 52% | 68% | 152 ms | 173 ms |
| hybrid (RRF) | 26% | 36% | 52% | 68% | 0.356 | 44% | 60% | 169 ms | 190 ms |
| hybrid + reranker | 46% | 66% | 70% | 80% | 0.573 | 64% | 76% | 8.8 s | 10.3 s |

### paraphrased set (25 facts x 2 languages), chunking = article-oai

| search | recall@1 | recall@3 | recall@5 | recall@10 | MRR@10 | AR recall@5 | FR recall@5 | search p50 | search p95 |
|---|---|---|---|---|---|---|---|---|---|
| keyword only (BM25) | 12% | 24% | 32% | 46% | 0.207 | 32% | 32% | 46 ms | 60 ms |
| vector only | 34% | 56% | 66% | 78% | 0.481 | 44% | 88% | 324 ms | 508 ms |
| hybrid (RRF) | 26% | 38% | 58% | 76% | 0.386 | 52% | 64% | 381 ms | 438 ms |
| hybrid + reranker | 52% | 72% | 76% | 78% | 0.612 | 68% | 84% | 7.2 s | 9.3 s |
