import re
from youtube_transcript_api import YouTubeTranscriptApi

YOUTUBE_ID_REGEX = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_ID_REGEX.search(url)
    return match.group(1) if match else None


def _fmt_mmss(seconds: float) -> str:
    s = int(seconds)
    mm = s // 60
    ss = s % 60
    return f"{mm:02d}:{ss:02d}"


def fetch_transcript_payload(video_id: str) -> dict:
    """
    Returns:
      {
        "text": "full transcript text ...",
        "timed_text": "[00:07] hello ...\n[00:10] ...",
      }
    Works with the library version you have (api.fetch()).
    """
    api = YouTubeTranscriptApi()
    data = api.fetch(video_id)

    # New object format: has .snippets (what you saw earlier)
    if hasattr(data, "snippets"):
        text = " ".join(snippet.text for snippet in data.snippets).strip()
        timed_lines = [f"[{_fmt_mmss(snippet.start)}] {snippet.text}" for snippet in data.snippets]
        timed_text = "\n".join(timed_lines).strip()
        return {"text": text, "timed_text": timed_text}

    # Older formats fallback
    if isinstance(data, list):
        text = " ".join(chunk.get("text", "") for chunk in data).strip()
        timed_lines = []
        for chunk in data:
            start = chunk.get("start", 0)
            timed_lines.append(f"[{_fmt_mmss(start)}] {chunk.get('text','')}")
        return {"text": text, "timed_text": "\n".join(timed_lines).strip()}

    if isinstance(data, dict):
        segments = data.get("transcript") or data.get("segments") or []
        text = " ".join(seg.get("text", "") for seg in segments).strip()
        timed_lines = []
        for seg in segments:
            start = seg.get("start", 0)
            timed_lines.append(f"[{_fmt_mmss(start)}] {seg.get('text','')}")
        return {"text": text, "timed_text": "\n".join(timed_lines).strip()}

    return {"text": str(data).strip(), "timed_text": str(data).strip()}


def explain_transcript_error(e: Exception) -> str:
    msg = (str(e) or "").lower()

    if "disabled" in msg:
        return "Captions are disabled for this video."
    if "no transcript" in msg or "not found" in msg:
        return "No transcript/captions found for this video."
    if "unavailable" in msg or "private" in msg:
        return "Video is unavailable (private/region/age restricted)."
    if "no element found" in msg:
        return "Couldn’t access captions (YouTube blocked request or no captions exist)."

    return str(e) or e.__class__.__name__