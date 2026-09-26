| Scenario | Correct | Avg seconds | Avg tool calls | Avg cost | High-confidence but wrong |
|---|---|---|---|---|---|
| schema_drift | 1/1 | 11.2 | 4.0 | $0.024 | 0 |
| null_spike | 1/1 | 13.5 | 7.0 | $0.032 | 0 |
| duplicates | 1/1 | 19.9 | 8.0 | $0.046 | 0 |
| stale_data | 1/1 | 14.8 | 5.0 | $0.031 | 0 |
| type_change | 1/1 | 9.5 | 4.0 | $0.022 | 0 |
| volume_drop | 1/1 | 11.8 | 3.0 | $0.021 | 0 |

**Overall: 6/6 correct (100%, 95% CI 61%-100%)** on claude-sonnet-5, judged by claude-opus-5.
Agent cost $0.18 total ($0.029 per incident); judge cost $0.03.
Runs without a usable report: 0; harness errors (not scored): 0.
