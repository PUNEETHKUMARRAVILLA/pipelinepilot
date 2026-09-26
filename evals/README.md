# evals/: does the agent find the right root cause?

```bash
python -m evals.run_evals --reps 1     # one run per failure type (about $0.25)
python -m evals.run_evals --reps 5     # the full 30 runs; runs already done are reused
python -m evals.run_evals --scenarios schema_drift,duplicates --reps 3 --variant v1
```

Each (scenario, rep):

1. Fresh warehouse, then one healthy pipeline run as the "normal" baseline.
2. Inject the failure with `pipeline/break_it.py` and run the pipeline so it fails (no Slack).
3. The real agent (`agent.investigate.investigate`) investigates.
4. A Claude Opus 5 judge compares the agent's `ROOT CAUSE:` line with the truth in
   `logs/injected_failure.json`, a file none of the agent's tools can read, and returns
   correct/incorrect with a one-line reason.

Your own warehouse is backed up first and restored afterwards.

Output in `runs/<variant>/`:

| File | Contents |
|---|---|
| `results.jsonl` | One row per run: correct, judge's reason, seconds, tool calls, tokens, confidence, status |
| `traces/` | Every step of each investigation (git-ignored; view them in the trace viewer) |
| `errors.jsonl` | Runs that broke before producing a report; logged, never scored |
| `summary.md` | The results table that goes in the main README |

Runs that stop early (`truncated`, `refusal`, no report) count as wrong but are listed separately,
so plumbing problems can't hide inside the accuracy number.

**Limits:** the judge grades the root cause only, not whether each evidence bullet is true.
The judge was checked on known answers first (the truth itself, a real wrong diagnosis,
"I don't know", an empty answer, the wrong column) and got all 6 right.
