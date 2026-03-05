# 💰 PolyMoney v2.0 — Polymarket Wallet Trade Tracker

Python script that monitors one or multiple wallets on Polymarket in real time. It polls the Polymarket Data API, detects new trades, and sends instant alerts via Telegram.

## Features

- Multi-wallet tracking via environment variables
- New trade detection with JSON-based state persistence
- Telegram notifications with full trade details (market, side, price, size, direct link)
- Optional filtering by specific markets (condition IDs)
- API rate limiting and error handling
- Smart warm-up to prevent duplicate alerts on startup

## Setup

### 1. Install dependencies
```bash
pip install requests
```

### 2. Set environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TARGET_WALLETS` | Yes | Comma-separated list of 0x wallet addresses |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for alerts |
| `TELEGRAM_CHAT_ID` | No | Telegram chat ID for alerts |
| `POLL_SECONDS` | No | Polling interval in seconds (default: 20) |
| `LIMIT` | No | Number of trades to fetch per request (default: 120) |
| `MARKET_CONDITION_IDS` | No | Comma-separated condition IDs to filter by |

### 3. Run
```bash
python PolyMoney_v2_0.py
```

## How It Works

1. On startup, fetches recent trades for each wallet (warm-up) and marks them as seen
2. Polls the Polymarket Data API every N seconds
3. Compares new trades against saved state (`state.json`)
4. Sends Telegram alerts for any unseen trades
5. Persists state to avoid duplicate notifications on restart

## Example Alert
```
[0x6a72...033ee]
Polymarket TRADE → Will Bitcoin hit $100k?
BUY Yes | size=50 | price=0.65 | ts=1706112000
Tx: 0xabc123...
Link: https://polymarket.com/event/...
```

## Tech Stack

- Python 3
- Polymarket Data API
- Telegram Bot API
- JSON file-based state persistence
