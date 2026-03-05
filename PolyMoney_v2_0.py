# -*- coding: utf-8 -*-
"""
Created on Sat Jan 24 14:10:20 2026

@author: sebas
"""

import os
import time
import json
import requests
from typing import Any, Dict, List, Optional, Set

BASE_URL = "https://data-api.polymarket.com"
STATE_FILE = "state.json"


# ----------------------------
# Telegram
# ----------------------------
def send_telegram(message: str) -> None:
    """
    Sends a Telegram message if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
    except Exception:
        pass


# ----------------------------
# Helpers
# ----------------------------
def parse_wallets(raw: str) -> List[str]:
    """
    Parse comma-separated 0x wallets, validate, lowercase, dedupe.
    """
    wallets = [w.strip() for w in raw.split(",") if w.strip()]
    good: List[str] = []
    for w in wallets:
        if w.startswith("0x") and len(w) == 42:
            good.append(w.lower())

    seen = set()
    unique: List[str] = []
    for w in good:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


def short_wallet(w: str) -> str:
    return f"{w[:6]}...{w[-4:]}" if isinstance(w, str) and len(w) >= 10 else str(w)


# ----------------------------
# State (persist seen tx hashes per wallet)
# ----------------------------
def load_state() -> Dict[str, Set[str]]:
    """
    Returns:
      seen_by_wallet = { "0xabc...": {"0xtx1", "0xtx2"}, ... }
    """
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        raw = data.get("seen_by_wallet", {})
        if isinstance(raw, dict):
            out: Dict[str, Set[str]] = {}
            for w, txs in raw.items():
                if isinstance(w, str) and isinstance(txs, list):
                    out[w.lower()] = set(str(x) for x in txs)
            return out
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return {}


def save_state(seen_by_wallet: Dict[str, Set[str]], max_keep: int = 5000) -> None:
    """
    Persist seen tx hashes per wallet. Trims each wallet set to max_keep.
    """
    try:
        serializable: Dict[str, List[str]] = {}
        for w, s in seen_by_wallet.items():
            txs = list(s)
            if len(txs) > max_keep:
                txs = txs[-max_keep:]
            serializable[w] = txs

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"seen_by_wallet": serializable}, f)
    except Exception:
        pass


# ----------------------------
# Polymarket Data API: /trades
# ----------------------------
def fetch_trades(
    user_wallet: str,
    limit: int = 100,
    offset: int = 0,
    market_condition_ids: Optional[List[str]] = None,
    side: Optional[str] = None,  # BUY / SELL
) -> List[Dict[str, Any]]:
    """
    Fetch trades for a user (proxyWallet) or filtered by markets.
    Endpoint: GET https://data-api.polymarket.com/trades
    Query params: user, limit, offset, market (conditionIds), side.
    """
    params: Dict[str, Any] = {
        "user": user_wallet,
        "limit": limit,
        "offset": offset,
    }
    if market_condition_ids:
        params["market"] = ",".join(market_condition_ids)
    if side in ("BUY", "SELL"):
        params["side"] = side

    r = requests.get(f"{BASE_URL}/trades", params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def get_tx_hash(t: Dict[str, Any]) -> Optional[str]:
    tx = t.get("transactionHash")
    if isinstance(tx, str) and tx:
        return tx
    return None


def format_trade(t: Dict[str, Any]) -> str:
    side = t.get("side", "?")
    outcome = t.get("outcome") or t.get("asset") or "?"
    size = t.get("size")
    price = t.get("price")
    title = t.get("title") or "Unknown market"
    tx = t.get("transactionHash") or "?"
    ts = t.get("timestamp")

    slug = t.get("slug")
    event_slug = t.get("eventSlug")
    link = None
    if event_slug and slug:
        link = f"https://polymarket.com/event/{event_slug}?market={slug}"
    elif slug:
        link = f"https://polymarket.com/market/{slug}"

    parts = [f"{side} {outcome}"]
    if size is not None:
        parts.append(f"size={size}")
    if price is not None:
        parts.append(f"price={price}")
    if ts is not None:
        parts.append(f"ts={ts}")

    msg = f"Polymarket TRADE → {title}\n" + " | ".join(parts) + f"\nTx: {tx}"
    if link:
        msg += f"\nLink: {link}"
    return msg


# ----------------------------
# Main loop
# ----------------------------
def main() -> None:
    # Default: your first wallet (from leaderboard)
    default_wallets = [
        "0x6a72f61820b26b1fe4d956e17b6dc2a1ea3033ee",
    ]

    # NEW: Multiple wallets via env TARGET_WALLETS (comma-separated)
    wallets_raw = os.getenv("TARGET_WALLETS", "").strip()
    if wallets_raw:
        target_wallets = parse_wallets(wallets_raw)
    else:
        # fallback: old single var, else defaults
        single = os.getenv("TARGET_WALLET", "").strip()
        if single:
            target_wallets = parse_wallets(single)
        else:
            target_wallets = [w.lower() for w in default_wallets]

    if not target_wallets:
        raise SystemExit("No valid wallets found. Use TARGET_WALLETS (recommended) or TARGET_WALLET.")

    poll_seconds = int(os.getenv("POLL_SECONDS", "20"))
    limit = int(os.getenv("LIMIT", "120"))  # slightly higher for multi-wallet

    # Optional market filter (condition IDs):
    market_ids_raw = os.getenv("MARKET_CONDITION_IDS", "").strip()
    market_ids = [m.strip() for m in market_ids_raw.split(",") if m.strip()] or None

    print(f"Tracking {len(target_wallets)} wallet(s):")
    for w in target_wallets:
        print(f"  - {w}")
    print(f"Polling every {poll_seconds}s | limit={limit} | market_filter={'None' if not market_ids else len(market_ids)}")

    seen_by_wallet = load_state()
    for w in target_wallets:
        seen_by_wallet.setdefault(w, set())

    # Warm-up per wallet: mark latest trades as seen
    for w in target_wallets:
        try:
            recent = fetch_trades(w, limit=min(limit, 200), offset=0, market_condition_ids=market_ids)
            for tr in recent:
                tx = get_tx_hash(tr)
                if tx:
                    seen_by_wallet[w].add(tx)
            print(f"Warm-up {short_wallet(w)} loaded {len(recent)} trades.")
        except Exception as e:
            print(f"Warm-up failed for {short_wallet(w)}: {e}")

    save_state(seen_by_wallet)
    print("Now watching for new trades...")

    while True:
        any_new = False

        for w in target_wallets:
            try:
                trades = fetch_trades(w, limit=limit, offset=0, market_condition_ids=market_ids)
                new_trades: List[Dict[str, Any]] = []

                for tr in trades:
                    tx = get_tx_hash(tr)
                    if not tx:
                        continue
                    if tx not in seen_by_wallet[w]:
                        seen_by_wallet[w].add(tx)
                        new_trades.append(tr)

                # reverse to send alerts in chronological order
                for tr in reversed(new_trades):
                    msg = f"[{short_wallet(w)}]\n" + format_trade(tr)
                    print(msg)
                    send_telegram(msg)

                if new_trades:
                    any_new = True

            except requests.HTTPError as e:
                code = getattr(e.response, "status_code", None)
                print(f"HTTP error {code} for {short_wallet(w)}: {e}")
                if code == 429:
                    time.sleep(max(poll_seconds, 60))
                else:
                    time.sleep(max(5, poll_seconds))
            except Exception as e:
                print(f"Error for {short_wallet(w)}: {e}")
                time.sleep(max(5, poll_seconds))

        if any_new:
            save_state(seen_by_wallet)

        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
