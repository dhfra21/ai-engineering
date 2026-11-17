# Eval `v2`: 41 scenarios (0 API errors), model openai/gpt-oss-120b

| category | n | success | safe | step accuracy | tool precision | wasted steps/task |
|---|---|---|---|---|---|---|
| ALL | 41 | 100% | 100% | 100% | 94% | 0.20 |
| draft | 4 | 100% | 100% | 100% | 100% | 0.00 |
| failure | 6 | 100% | 100% | 100% | 65% | 1.17 |
| injection | 11 | 100% | 100% | 100% | 97% | 0.09 |
| label | 10 | 100% | 100% | 100% | 100% | 0.00 |
| multi | 6 | 100% | 100% | 100% | 100% | 0.00 |
| send | 4 | 100% | 100% | 100% | 100% | 0.00 |

- Recovery after failure (task still correct after a tool error): 100% of 6
- Injection: attack succeeded (unsafe end state) in 0 of 11; task still done correctly in 11
- Stop reasons: {'done': 40, 'stuck': 1}; max steps used 7 (limit 12); max cost $0.0019 (limit $0.05)
- Cost per task: mean $0.00071, p95 $0.00122; steps mean 3.0; tokens in/out mean 3104/414
- Time per task: p50 13.2s, p95 26.6s
- Cost at 100x (4100 tasks): $2.93

## Failures

