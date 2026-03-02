import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from src.config import TELEGRAM_BOT_TOKEN
from src.bot.handlers import start, help_cmd, on_message

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)

def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    return app

async def main() -> None:
    app = build_app()

    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message"])

    print("Bot is running... Press Ctrl+C to stop.")
    # keep alive
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())