"""Post the agent's report to Slack through an incoming webhook."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()


def format_report(trace: dict) -> str:
    """Turn an agent trace into a Slack message."""
    event = trace["event"]
    header = (f":rotating_light: *Incident: {event['pipeline']} failed* at step "
              f"`{event['failed_step']}` (run `{event['run_id']}`)")
    footer = (f"_{len(trace['steps'])} tool calls, {trace['seconds']}s, "
              f"{trace['usage']['input_tokens']} in / {trace['usage']['output_tokens']} out tokens_")
    return f"{header}\n\n{trace['report']}\n\n{footer}"


def post_to_slack(text: str) -> bool:
    """Send a message to the channel behind SLACK_WEBHOOK_URL. Returns True if Slack accepted it."""
    url = os.getenv("SLACK_WEBHOOK_URL")
    if not url:
        print("SLACK_WEBHOOK_URL is not set in .env, so nothing was posted.")
        return False
    resp = requests.post(url, json={"text": text}, timeout=10)
    if not resp.ok:
        print(f"Slack rejected the message: {resp.status_code} {resp.text}")
    return resp.ok
