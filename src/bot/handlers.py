import re
from telegram import Update
from telegram.ext import ContextTypes

from src.services.youtube import (
    extract_video_id,
    fetch_transcript,
    explain_transcript_error,
)
from src.services.summarizer import summarise_text

YOUTUBE_URL_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[^\s]+",
    re.IGNORECASE,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Hi! Send me a YouTube link and I’ll summarise it via the transcript 🙂"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send a YouTube link like:\n"
        "https://youtu.be/VIDEO_ID\n"
        "or\n"
        "https://www.youtube.com/watch?v=VIDEO_ID"
    )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    match = YOUTUBE_URL_REGEX.search(text)
    if not match:
        await update.message.reply_text("I didn’t spot a YouTube link. Try sending one!")
        return

    url = match.group(0)
    await update.message.reply_text("⏳ Fetching transcript...")

    video_id = extract_video_id(url)
    if not video_id:
        await update.message.reply_text("❌ Could not extract video ID from that link.")
        return

    try:
        transcript_text = fetch_transcript(video_id)
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to fetch transcript.\nReason: {explain_transcript_error(e)}"
        )
        return

    await update.message.reply_text("🧠 Summarising...")

    try:
        summary = summarise_text(transcript_text)

        # Telegram message length limit safety
        if len(summary) > 3800:
            summary = summary[:3800] + "..."

        await update.message.reply_text(summary)

    except Exception as e:
        # If summarising fails, fall back to transcript preview so you still get something
        preview = transcript_text[:800].strip()
        await update.message.reply_text(
            f"❌ Summarising failed.\nReason: {e}\n\n✅ Transcript preview instead:\n\n{preview}..."
        )