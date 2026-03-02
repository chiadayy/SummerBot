# YouTube Summariser Telegram Bot

A Telegram bot that converts YouTube videos into structured, readable summaries with live progress updates and multiple output formats.

The system handles long transcripts via chunking, provides different summary styles on demand, and allows users to generate multiple views of the same video without reprocessing.

---

## Overview

This project demonstrates an end-to-end AI application pipeline:

User → Telegram Bot → YouTube transcript extraction → Chunking → Claude/OpenAI summarisation → Structured response → Telegram delivery

---

## Key Features

- Multiple summary modes:
  - TL;DR
  - Key Takeaways
  - Explain Like I'm 5 (analogy-driven)
  - Detailed Summary (paragraph format)
  - Key Moments (timestamped highlights)

- Automatic handling of long videos via transcript chunking  
- Live progress updates inside Telegram  
- Resilient API retry handling  
- Structured prompt design for consistent outputs  
- Ability to reuse the same video for multiple summary formats  
- Clean conversational Telegram UX  

---

## System Flow

1. User starts the bot and selects a summary mode  
2. User sends a YouTube link  
3. Bot extracts the video ID  
4. Transcript is fetched from YouTube  
5. Long transcripts are chunked  
6. Each chunk is summarised via Claude  
7. Final structured output is generated  
8. User can request additional formats without re-fetching  

---

## Project Structure

src/
├── bot/
│   └── handlers.py       # Telegram handlers and conversation flow
├── services/
│   ├── summarizer.py     # Claude/OpenAI prompting, chunking, progress logic
│   └── youtube.py        # YouTube transcript extraction
├── config.py
└── main.py

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd <repo-name>

2. Create a virtual environment

python -m venv .venv
source .venv/bin/activate   # macOS / Linux

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

Create a .env file in the project root:

TELEGRAM_BOT_TOKEN=your_telegram_token
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_claude_key

Do not commit this file.

⸻

Running the Bot

python -m src.main

After starting the service, open Telegram and message your bot.

⸻

Example Usage
	1.	Send /start
	2.	Select a summary mode
	3.	Paste a YouTube link
	4.	Observe live progress updates
	5.	Receive structured output

Users can immediately request another format for the same video.

