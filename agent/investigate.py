"""The agent loop: give Claude the failure event + tools, let it investigate, print the report.

Run:  python -m agent.investigate
Reads logs/last_failure.json (written by pipeline/run.py) and saves the full trace
to logs/trace_<run_id>.json so you can see every step it took.
"""
import json
import os
import sys
import time

import anthropic
from dotenv import load_dotenv

from agent.tools import TOOL_SCHEMAS, TOOLS
from pipeline.config import LAST_FAILURE, LOG_DIR

load_dotenv()
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_STEPS = 10

SYSTEM_PROMPT = """You are PipelinePilot, an on-call data engineer investigating a failed data pipeline.
You can only READ: logs, the raw source file, and the DuckDB warehouse via read-only tools.

How to work:
1. Start with the run's logs to see which step failed and the exact error.
2. Form a hypothesis, then use the tools to confirm it with evidence. Compare against the
   last successful run or the existing staging table when useful.
3. Stop as soon as the evidence is conclusive. Do not guess.

Finish with a report in exactly this format:
ROOT CAUSE: <one sentence>
EVIDENCE:
- <fact from a tool result>
- <fact from a tool result>
SUGGESTED FIX: <concrete change, for a human to approve>
CONFIDENCE: <high | medium | low>
"""


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    try:
        return str(TOOLS[name](**args)), False
    except Exception as e:  # noqa: BLE001 - errors go back to the model as information
        return f"Tool error: {type(e).__name__}: {e}", True


def investigate(event: dict) -> dict:
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    messages = [{"role": "user", "content": "A pipeline run just failed. Investigate it.\n\n"
                 + json.dumps(event, indent=2)}]
    trace = {"event": event, "model": MODEL, "steps": [], "report": None}
    usage = {"input_tokens": 0, "output_tokens": 0}
    started = time.time()

    for step in range(1, MAX_STEPS + 1):
        # The model thinks before answering and thinking counts toward max_tokens,
        # so leave plenty of room or the report gets cut off before it is written.
        resp = client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM_PROMPT,
                                      tools=TOOL_SCHEMAS, messages=messages)
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        for block in resp.content:
            if block.type == "text" and block.text.strip() and resp.stop_reason == "tool_use":
                print(f"\n[step {step}] thinking: {block.text.strip()}")

        trace["stop_reason"] = resp.stop_reason
        trace["served_model"] = resp.model  # what actually answered, not what we asked for
        if resp.stop_reason == "end_turn":
            trace["report"] = "".join(b.text for b in resp.content if b.type == "text")
            break
        if resp.stop_reason != "tool_use":  # max_tokens, refusal, ...: no usable report
            trace["report"] = f"Stopped early (stop_reason={resp.stop_reason}) without a report."
            break

        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            print(f"[step {step}] tool: {block.name}({json.dumps(block.input)})")
            output, is_error = run_tool(block.name, block.input)
            trace["steps"].append({"step": step, "tool": block.name, "input": block.input,
                                   "output": output[:4000], "error": is_error})
            results.append({"type": "tool_result", "tool_use_id": block.id,
                            "content": output[:8000], "is_error": is_error})
        messages.append({"role": "user", "content": results})
    else:
        trace["report"] = f"Stopped after {MAX_STEPS} steps without a conclusion."

    trace["seconds"] = round(time.time() - started, 1)
    trace["usage"] = usage
    return trace


def main() -> int:
    if not LAST_FAILURE.exists():
        print("No failure to investigate. Break the pipeline first:\n"
              "  python -m pipeline.break_it schema_drift && python -m pipeline.run")
        return 1
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")
        return 1

    event = json.loads(LAST_FAILURE.read_text())
    print(f"Investigating {event['pipeline']} run {event['run_id']} (failed at '{event['failed_step']}')...")
    trace = investigate(event)

    out = LOG_DIR / f"trace_{event['run_id']}.json"
    out.write_text(json.dumps(trace, indent=2, default=str))
    print("\n" + "=" * 60 + "\n" + (trace["report"] or "") + "\n" + "=" * 60)
    print(f"{len(trace['steps'])} tool calls, {trace['seconds']}s, "
          f"{trace['usage']['input_tokens']} in / {trace['usage']['output_tokens']} out tokens")
    print(f"Full trace: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
