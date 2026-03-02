import os
import requests

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


def summarise_text(transcript: str) -> str:
    transcript = transcript.strip()

    # Keep request size sane (we’ll do proper chunking later)
    if len(transcript) > 12000:
        transcript = transcript[:12000]

    prompt = f"""
You are a helpful summariser.

Summarise the YouTube transcript below.

Output format:
1) TL;DR (1-2 sentences)
2) Key points (5 bullets)
3) Notable terms/people (up to 5)

Transcript:
{transcript}
""".strip()

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 800,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}],
    }

    r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"Claude API error {r.status_code}: {r.text}")

    data = r.json()
    # Anthropic returns: {"content":[{"type":"text","text":"..."}], ...}
    return data["content"][0]["text"].strip()