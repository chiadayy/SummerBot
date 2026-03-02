import re
from youtube_transcript_api import YouTubeTranscriptApi

YOUTUBE_ID_REGEX = re.compile(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})")


def extract_video_id(url: str) -> str | None:
    match = YOUTUBE_ID_REGEX.search(url)
    return match.group(1) if match else None


def fetch_transcript(video_id: str) -> str:
    api = YouTubeTranscriptApi()
    data = api.fetch(video_id)

    # 🔥 Case 1: new object format (what you're seeing)
    if hasattr(data, "snippets"):
        return " ".join(snippet.text for snippet in data.snippets).strip()

    # 🔥 Case 2: list of dicts (older format)
    if isinstance(data, list):
        return " ".join(chunk.get("text", "") for chunk in data).strip()

    # 🔥 Case 3: dict fallback
    if isinstance(data, dict):
        segments = data.get("transcript") or data.get("segments") or []
        return " ".join(seg.get("text", "") for seg in segments).strip()

    return str(data).strip()


def explain_transcript_error(e: Exception) -> str:
    msg = (str(e) or "").lower()

    # common “no transcript” signals
    if "transcript" in msg and ("not" in msg or "no" in msg):
        return "No transcript/captions found for this video."
    if "disabled" in msg:
        return "Captions are disabled for this video."
    if "unavailable" in msg or "private" in msg:
        return "Video is unavailable (private/region/age restricted)."
    if "no element found" in msg:
        return "Couldn’t access captions (YouTube blocked the request or no captions exist)."

    # fallback
    return str(e) or e.__class__.__name__