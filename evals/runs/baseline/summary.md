| Scenario | Correct | Avg seconds | Avg tool calls | Avg cost | High-confidence but wrong |
|---|---|---|---|---|---|
| schema_drift | 5/5 | 11.4 | 4.2 | $0.023 | 0 |
| null_spike | 5/5 | 13.2 | 6.2 | $0.029 | 0 |
| duplicates | 5/5 | 21.6 | 8.2 | $0.053 | 0 |
| stale_data | 5/5 | 17.6 | 5.6 | $0.037 | 0 |
| type_change | 5/5 | 11.3 | 4.8 | $0.025 | 0 |
| volume_drop | 5/5 | 10.6 | 3.4 | $0.021 | 0 |

**Overall: 30/30 correct (100%, 95% CI 89%-100%)** on claude-sonnet-5, judged by claude-opus-5.
Agent cost $0.94 total ($0.031 per incident); judge cost $0.18.
Runs without a usable report: 0; harness errors (not scored): 0.
