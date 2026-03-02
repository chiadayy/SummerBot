import os
import requests
import time

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"

MODEL = "claude-3-haiku-20240307"


def _call_claude(user_prompt: str, max_tokens: int = 800, temperature: float = 0.3) -> str:
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_prompt}],
    }

    r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=90)

    # basic retry for rate-limit/transient issues
    if r.status_code in (429, 500, 502, 503, 504):
        time.sleep(2)
        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=90)

    if r.status_code >= 400:
        raise RuntimeError(f"Claude API error {r.status_code}: {r.text}")

    data = r.json()
    return data["content"][0]["text"].strip()


def _chunk_text(text: str, chunk_size: int = 9000, overlap: int = 600) -> list[str]:
    """
    Character-based chunking with overlap so we don't cut off context too harshly.
    - chunk_size: target chunk length
    - overlap: repeated context between chunks
    """
    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def summarise_text(transcript: str, on_progress=None) -> str:
    transcript = transcript.strip()
    if not transcript:
        return "No transcript text found to summarise."

    # ✅ Always chunk (even if it's just 1 chunk)
    chunks = _chunk_text(transcript, chunk_size=9000, overlap=600)

    if on_progress:
        on_progress(f"🧩 Preparing summary — {len(chunks)} part(s) detected...")

    chunk_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        if on_progress:
            on_progress(f"🧠 Summarising part {i}/{len(chunks)}...")

        chunk_prompt = f"""
You are summarising PART {i} of {len(chunks)} of a YouTube transcript.

Write:
- 3 bullet key points
- 1 sentence of what this part mainly covers
Keep it concise.

PART {i} TRANSCRIPT:
{chunk}
""".strip()

        part_summary = _call_claude(chunk_prompt, max_tokens=300, temperature=0.2)
        chunk_summaries.append(f"PART {i} SUMMARY:\n{part_summary}")

    combined = "\n\n".join(chunk_summaries)

    if on_progress:
        on_progress("🧠 Combining part summaries into final summary...")

    final_prompt = f"""
You are given summaries of each part of a YouTube transcript.
Combine them into a single coherent summary.

Output format:
1) TL;DR (1-2 sentences)
2) Key points (7 bullets)
3) Actionable takeaways (3 bullets)
4) Notable terms/people (up to 8)

PART SUMMARIES:
{combined}
""".strip()

    return _call_claude(final_prompt, max_tokens=900, temperature=0.3)
    transcript = transcript.strip()
    if not transcript:
        return "No transcript text found to summarise."

    # If short enough, do single-pass summary
    if len(transcript) <= 12000:
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
        return _call_claude(prompt, max_tokens=800, temperature=0.3)

    # Long transcript: chunk -> per-chunk summaries -> final summary
    chunks = _chunk_text(transcript, chunk_size=9000, overlap=600)

    if on_progress:
        on_progress(f"🧩 Long video detected — splitting into {len(chunks)} parts...")

    chunk_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        if on_progress:
            on_progress(f"🧠 Summarising part {i}/{len(chunks)}...")

        chunk_prompt = f"""
You are summarising PART {i} of {len(chunks)} of a long YouTube transcript.

Write:
- 3 bullet key points
- 1 sentence of what this part mainly covers
Keep it concise.

PART {i} TRANSCRIPT:
{chunk}
""".strip()

        part_summary = _call_claude(chunk_prompt, max_tokens=300, temperature=0.2)
        chunk_summaries.append(f"PART {i} SUMMARY:\n{part_summary}")

    combined = "\n\n".join(chunk_summaries)

    final_prompt = f"""
You are given summaries of each part of a long YouTube transcript.
Combine them into a single coherent summary.

Output format:
1) TL;DR (1-2 sentences)
2) Key points (7 bullets)
3) Actionable takeaways (3 bullets)
4) Notable terms/people (up to 8)

PART SUMMARIES:
{combined}
""".strip()

    return _call_claude(final_prompt, max_tokens=900, temperature=0.3)