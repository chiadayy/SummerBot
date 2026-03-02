import os
import random
import requests
import time

ANTHROPIC_API_KEY = (os.getenv("ANTHROPIC_API_KEY") or "").strip()
if not ANTHROPIC_API_KEY:
    raise RuntimeError("Missing ANTHROPIC_API_KEY in .env")

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
MODEL = "claude-3-haiku-20240307"


def _call_claude(user_prompt: str, max_tokens: int = 900, temperature: float = 0.3) -> str:
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

    retry_statuses = {429, 500, 502, 503, 504, 529}
    delays = [1.0, 2.0, 4.0]

    last_resp = None
    for delay in delays:
        r = requests.post(ANTHROPIC_URL, headers=headers, json=payload, timeout=90)

        if r.status_code < 400:
            data = r.json()
            return data["content"][0]["text"].strip()

        last_resp = r
        if r.status_code in retry_statuses:
            time.sleep(delay + random.uniform(0, 0.5))
            continue

        raise RuntimeError(f"Claude API error {r.status_code}: {r.text}")

    raise RuntimeError(f"Claude API error {last_resp.status_code}: {last_resp.text}")


def _chunk_text(text: str, chunk_size: int = 9000, overlap: int = 600) -> list[str]:
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


def _bar(done: int, total: int, width: int = 10) -> str:
    total = max(total, 1)
    done = max(0, min(done, total))
    filled = int(width * done / total)

    bar = "▰" * filled + "▱" * (width - filled)
    return f"Progress {bar} {done}/{total}"


STYLE_MAP = {
    "tldr": """Output EXACTLY in this format:

TL;DR: <one sentence>

• <bullet 1>
• <bullet 2>
• <bullet 3>

Best for: <who should watch in 6–10 words>

Rules:
- Only use information clearly stated in the transcript.
- If something is unclear, write "Not mentioned".
- Keep it short and Telegram-friendly.
- Each bullet must be <= 12 words.
""",

    "takeaways": """Output EXACTLY in this format:

Key Takeaways
1) <takeaway 1>
2) <takeaway 2>
3) <takeaway 3>
4) <takeaway 4>
5) <takeaway 5>
6) <takeaway 6>

If you only remember one thing: <one sentence>

Rules:
- Takeaways must be actionable (principle, warning, recommendation, or decision rule).
- Each takeaway must be <= 14 words.
- Avoid repeating the same idea.
- Do not invent facts; if unclear, write "Not mentioned".
""",

    "eli5": """Explain the topic to a 5-year-old using a friendly analogy.

Output EXACTLY in this format:

Explaining like you're 5 👶

<Big idea in one simple sentence>

Think of it like this:
<one short analogy using everyday objects (toys, food, school, etc.)>

What this means:
<simple explanation in very easy language>

Rules:
- Use short, simple sentences.
- Avoid jargon; if needed, explain it simply.
- Use ONE clear child-friendly analogy.
- Tone should be warm and friendly, not childish or cringe.
- Do not invent facts; if unclear, write "Not mentioned".
""",

    "detailed": """Write a structured, readable summary in paragraph form.

Output EXACTLY in this format:

Overview
<one concise paragraph>

Main Insights
<one paragraph explaining the core ideas>

Key Evidence / Examples
<one paragraph with notable examples or proof points>

Why It Matters
<one short paragraph on implications>

Rules:
- Use full sentences. No bullet points.
- Be clear, professional, and easy to read.
- Keep paragraphs compact (3–5 sentences each).
- Do not invent facts; if unclear, write "Not mentioned".
""",
}

def summarise_transcript(transcript: str, style: str, on_progress=None) -> str:
    transcript = transcript.strip()
    if not transcript:
        return "No transcript text found to summarise."

    if style not in STYLE_MAP:
        style = "detailed"

    chunks = _chunk_text(transcript, chunk_size=9000, overlap=600)

    total_steps = len(chunks) + 1
    step = 0

    def progress(msg: str):
        if on_progress:
            on_progress(msg)

    progress(f"🧩 Preparing summary...\n{_bar(step, total_steps)}")

    part_summaries = []
    for i, chunk in enumerate(chunks, start=1):
        progress(f"🧠 Summarising part {i}/{len(chunks)}...\n{_bar(step, total_steps)}")

        chunk_prompt = f"""
You are summarising PART {i} of {len(chunks)} of a YouTube transcript.

Return:
- 4 bullets of key points in this part
- 1 sentence: what this part mainly covers

Transcript:
{chunk}
""".strip()

        part_summary = _call_claude(chunk_prompt, max_tokens=280, temperature=0.2)
        part_summaries.append(f"PART {i}:\n{part_summary}")

        step += 1
        progress(f"🧠 Finished part {i}/{len(chunks)}\n{_bar(step, total_steps)}")

    progress(f"🧠 Combining into final output...\n{_bar(step, total_steps)}")

    combined = "\n\n".join(part_summaries)

    final_prompt = f"""
You will generate the final output based on part summaries.

Required style:
{STYLE_MAP[style]}

If possible, include:
- 1 "So what?" line (why it matters)
- 1 short list of terms/people (up to 6)

PART SUMMARIES:
{combined}
""".strip()

    final = _call_claude(final_prompt, max_tokens=900, temperature=0.3)

    step += 1
    progress(f"✅ Summary ready!\n{_bar(step, total_steps)}")
    return final


def key_moments(timed_text: str, on_progress=None) -> str:
    """
    timed_text is lines like:
      [00:07] ...
    """
    timed_text = timed_text.strip()
    if not timed_text:
        return "No timestamped transcript available."

    # Keep payload sane (still works well)
    if len(timed_text) > 18000:
        timed_text = timed_text[:18000]

    if on_progress:
        on_progress("⏱ Finding key moments...")

    prompt = f"""
From the timestamped transcript below, pick 6–10 KEY MOMENTS.

Rules:
- Each line MUST start with the timestamp in [MM:SS]
- Keep each moment title short (max ~8 words)
- Format exactly like this:

[MM:SS] Title — 1 short sentence

Timestamped transcript:
{timed_text}
""".strip()

    return _call_claude(prompt, max_tokens=800, temperature=0.2)