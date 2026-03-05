# PolyMoney — Polymarket Wallet Trade Tracker
Python script that monitors one or multiple wallets on Polymarket in real time. It polls the Polymarket Data API, detects new trades, and sends instant alerts via Telegram.
Key features:
  Multi-wallet tracking via environment variables
  New trade detection with JSON-based state persistence
  Telegram notifications with full trade details (market, side, price, size, direct link)
  Optional filtering by specific markets (condition IDs)
  API rate limiting and error handling
  Smart warm-up to prevent duplicate alerts on startup
