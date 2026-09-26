"""See what the agent did: every incident it investigated, step by step, plus eval scores.

Run:  streamlit run app/trace_viewer.py
Reads the trace files already on disk (logs/trace_*.json, evals/runs/*), so it makes no API calls.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))  # `streamlit run` only puts app/ on the path
from pipeline.config import LOG_DIR  # noqa: E402

EVAL_RUNS = ROOT / "evals" / "runs"
PRICES = {"claude-sonnet-5": (2.00, 10.00), "claude-opus-5": (5.00, 25.00)}  # $ per million tokens


def cost(model: str, usage: dict) -> float:
    price_in, price_out = PRICES.get(model, (0, 0))
    return (usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1_000_000


def load_traces() -> list[tuple[Path, dict]]:
    paths = sorted(LOG_DIR.glob("trace_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [(p, json.loads(p.read_text())) for p in paths]


def show_incident(trace: dict) -> None:
    event = trace["event"]
    st.subheader(f"{event['pipeline']} failed at `{event['failed_step']}`")
    st.caption(f"Run {event['run_id']} · failed at {event['failed_at']}")
    st.error(event["error"])

    usage = trace.get("usage", {"input_tokens": 0, "output_tokens": 0})
    model = trace.get("served_model") or trace.get("model", "")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tool calls", len(trace["steps"]))
    c2.metric("Seconds", trace.get("seconds", "-"))
    c3.metric("Tokens (in / out)", f"{usage['input_tokens']:,} / {usage['output_tokens']:,}")
    c4.metric("Cost", f"${cost(model, usage):.3f}")

    st.markdown("#### What the agent did")
    for s in trace["steps"]:
        args = ", ".join(f"{k}={v!r}" for k, v in s["input"].items())
        icon = "⚠️" if s.get("error") else "🔧"
        with st.expander(f"{icon} Step {s['step']}: `{s['tool']}({args})`"):
            st.code(s["output"], language="sql" if s["tool"] == "get_pipeline_code" else None)

    st.markdown("#### Report")
    if trace.get("stop_reason") not in (None, "end_turn"):
        st.warning(f"The agent stopped early (stop_reason={trace['stop_reason']}).")
    st.markdown(trace.get("report") or "_No report._")


def show_evals() -> None:
    variants = sorted(p for p in EVAL_RUNS.glob("*") if (p / "results.jsonl").exists())
    if not variants:
        st.info("No eval results yet. Run: `python -m evals.run_evals --reps 1`")
        return
    variant = st.selectbox("Eval run", variants, format_func=lambda p: p.name)
    rows = [json.loads(line) for line in (variant / "results.jsonl").read_text().splitlines()]
    right = sum(r["grade"]["correct"] for r in rows)
    c1, c2, c3 = st.columns(3)
    c1.metric("Correct root cause", f"{int(right)} / {len(rows)}")
    c2.metric("Avg seconds", f"{sum(r['latency_s'] for r in rows) / len(rows):.1f}")
    c3.metric("Avg cost per incident", f"${sum(cost(r['model'], r['usage']) for r in rows) / len(rows):.3f}")
    st.dataframe(
        [{"scenario": r["prompt_id"], "rep": r["rep"], "correct": "✅" if r["grade"]["correct"] else "❌",
          "seconds": r["latency_s"], "tool calls": r["tool_calls"], "confidence": r["confidence"],
          "agent's root cause": r["root_cause"], "judge's reason": r["explanation"]["correct"]}
         for r in rows],
        hide_index=True, width="stretch",
    )


st.set_page_config(page_title="PipelinePilot", page_icon="🛩️", layout="wide")
st.title("🛩️ PipelinePilot")
tab_incidents, tab_evals = st.tabs(["Incidents", "Eval results"])

with tab_incidents:
    traces = load_traces()
    if not traces:
        st.info("No incidents yet. Break the pipeline and let the agent investigate.")
    else:
        labels = [f"{datetime.fromtimestamp(p.stat().st_mtime):%b %d %H:%M} · "
                  f"{t['event']['failed_step']} · {t['event']['run_id']}" for p, t in traces]
        choice = st.selectbox("Incident (newest first)", range(len(traces)), format_func=lambda i: labels[i])
        show_incident(traces[choice][1])

with tab_evals:
    show_evals()
