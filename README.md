# YouTube Summariser Telegram Bot

A Telegram bot that converts YouTube videos into structured summaries on demand.
The system supports multiple summary styles, handles long transcripts via chunking, and provides live progress updates during processing.

The architecture is model-agnostic and can work with either Claude (Anthropic) or OpenAI models.

## What the Bot Does

• User selects a summary mode
• User pastes a YouTube link
• Bot fetches the transcript
• Long transcripts are automatically chunked
• AI generates a structured summary
• User can request other formats using the same video


## Supported Output Modes

• TL;DR
• Key Takeaways
• Explain Like I’m 5
• Detailed Summary
• Key Moments (timestamped)


## Project Structure

src/
├── bot/handlers.py — Telegram conversation flow
├── services/summarizer.py — chunking, prompting, progress logic
├── services/youtube.py — transcript extraction
├── config.py
└── main.py

## Setup
	1.	Create and activate a virtual environment
	2.	Install dependencies from requirements.txt
	3.	Create a .env file in the project root with:

TELEGRAM_BOT_TOKEN=your_token

either:
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key 

Do not commit the .env file.

## To Run

python -m src.main

Then open Telegram and start the bot using /start.