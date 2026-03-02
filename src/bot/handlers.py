import asyncio
import re
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.services.youtube import (
    extract_video_id,
    fetch_transcript_payload,
    explain_transcript_error,
)
from src.services.summarizer import summarise_transcript, key_moments

YOUTUBE_URL_REGEX = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/)[^\s]+",
    re.IGNORECASE,
)

MODES = [
    ("TL;DR", "tldr"),
    ("Key Takeaways", "takeaways"),
    ("Explain Like I'm 5", "eli5"),
    ("Detailed Summary", "detailed"),
    ("Key Moments (Timestamps)", "moments"),
]


def _mode_menu(include_end: bool) -> InlineKeyboardMarkup:
    rows = []
    for label, key in MODES:
        rows.append([InlineKeyboardButton(label, callback_data=f"mode:{key}")])
    if include_end:
        rows.append([InlineKeyboardButton("End", callback_data="mode:end")])
    return InlineKeyboardMarkup(rows)


def _pretty_mode(mode: str) -> str:
    return {
        "tldr": "TL;DR",
        "takeaways": "Key Takeaways",
        "eli5": "Explain Like I'm 5",
        "detailed": "Detailed Summary",
        "moments": "Key Moments (Timestamped highlights)",
    }.get(mode, mode)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text(
        "Choose what you want me to generate 👇",
        reply_markup=_mode_menu(include_end=False),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Type /start to choose a summary mode.")


# -----------------------------
# Shared generator (reuses cache)
# -----------------------------
async def _generate_from_cache(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str) -> None:
    transcript_text = context.user_data.get("transcript_text", "")
    timed_text = context.user_data.get("timed_text", "")

    if not transcript_text and mode != "moments":
        await update.effective_chat.send_message("I don’t have a cached transcript yet. Paste a YouTube link 🙂")
        return

    if mode == "moments" and not timed_text:
        await update.effective_chat.send_message("I don’t have timestamped transcript yet. Paste a YouTube link 🙂")
        return

    # Live progress message
    progress_msg = await update.effective_chat.send_message("🧠 Starting...")
    loop = asyncio.get_running_loop()
    last_progress = {"t": 0.0}

    async def progress_cb(msg: str):
        try:
            await progress_msg.edit_text(msg)
        except Exception:
            pass

    def on_progress_from_thread(msg: str):
        now = time.time()
        if now - last_progress["t"] < 1.0:
            return
        last_progress["t"] = now
        loop.call_soon_threadsafe(lambda: asyncio.create_task(progress_cb(msg)))

    try:
        if mode == "moments":
            output = await asyncio.to_thread(
                key_moments,
                timed_text,
                on_progress=on_progress_from_thread,
            )
        else:
            output = await asyncio.to_thread(
                summarise_transcript,
                transcript_text,
                mode,
                on_progress=on_progress_from_thread,
            )

        if len(output) > 3800:
            output = output[:3800] + "..."

        await update.effective_chat.send_message(output)

        # Ask what else they want using same link
        await update.effective_chat.send_message(
            "Want another output using the same link?",
            reply_markup=_mode_menu(include_end=True),
        )

    except Exception as e:
        reason = str(e)
        if "overloaded" in reason.lower() or "529" in reason:
            reason = "Claude is overloaded right now. Try again in a bit."

        preview = (transcript_text[:800] or "").strip()
        await update.effective_chat.send_message(
            f"❌ Generation failed.\nReason: {reason}\n\n✅ Transcript preview instead:\n\n{preview}..."
        )
        await update.effective_chat.send_message(
            "Try again or choose another option:",
            reply_markup=_mode_menu(include_end=True),
        )


# -----------------------------
# Button handler
# -----------------------------
async def on_mode_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if data == "mode:end":
        context.user_data.clear()
        await query.edit_message_text("Ended ✅ Type /start to begin again.")
        return

    mode = data.split(":", 1)[1]
    context.user_data["mode"] = mode

    # ✅ If we already have a cached link/transcript, generate immediately
    if context.user_data.get("video_id") and (
        context.user_data.get("transcript_text") or context.user_data.get("timed_text")
    ):
        await query.edit_message_text(
            f"✅ Ok — generating **{_pretty_mode(mode)}** using the same link...",
            parse_mode="Markdown",
        )
        await _generate_from_cache(update, context, mode)
        return

    # Otherwise, ask for link (first-time)
    await query.edit_message_text(
        f"✅ Ok understood — you want **{_pretty_mode(mode)}**.\n\nNow paste the YouTube link 🙂",
        parse_mode="Markdown",
    )


# -----------------------------
# Message handler (expects link)
# -----------------------------
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()

    mode = context.user_data.get("mode")
    if not mode:
        await update.message.reply_text(
            "Pick an option first 👇",
            reply_markup=_mode_menu(include_end=False),
        )
        return

    match = YOUTUBE_URL_REGEX.search(text)
    if not match:
        await update.message.reply_text("I didn’t spot a YouTube link. Paste a YouTube URL 🙂")
        return

    url = match.group(0)
    video_id = extract_video_id(url)
    if not video_id:
        await update.message.reply_text("❌ Could not extract video ID from that link.")
        return

    # Fetch transcript only if new video
    cached_video_id = context.user_data.get("video_id")
    if cached_video_id != video_id:
        await update.message.reply_text("⏳ Fetching transcript...")

        try:
            payload = fetch_transcript_payload(video_id)
        except Exception as e:
            await update.message.reply_text(
                f"❌ Failed to fetch transcript.\nReason: {explain_transcript_error(e)}"
            )
            return

        context.user_data["video_id"] = video_id
        context.user_data["transcript_text"] = payload.get("text", "")
        context.user_data["timed_text"] = payload.get("timed_text", "")

    # Now generate using cache
    await _generate_from_cache(update, context, mode)