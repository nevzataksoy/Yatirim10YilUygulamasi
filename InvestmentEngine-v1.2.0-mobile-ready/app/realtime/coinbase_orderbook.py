from __future__ import annotations

import json
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

import websocket


@dataclass(slots=True)
class BookMetrics:
    product: str
    ts: str
    spread_bps: float
    bid_depth_usd: float
    ask_depth_usd: float
    imbalance: float
    microprice: float
    ofi: float
    trade_imbalance: float
    trade_notional_usd: float
    trade_gap_count: int
    sample_window_seconds: int


class CoinbaseOrderBookWorker:
    """Public Coinbase Exchange execution-observation worker.

    `level2_batch` provides the maintained book without authentication. `matches`
    adds executed-trade flow. Only derived snapshots are persisted by the engine;
    raw order-book/trade messages are intentionally not stored.
    """

    URL = "wss://ws-feed.exchange.coinbase.com"

    def __init__(self, products: tuple[str, ...] = ("BTC-USD", "ETH-USD"), depth_levels: int = 20) -> None:
        self.products = products
        self.depth_levels = depth_levels
        self.bids: dict[str, dict[float, float]] = defaultdict(dict)
        self.asks: dict[str, dict[float, float]] = defaultdict(dict)
        self.lock = threading.Lock()
        self.ws: websocket.WebSocketApp | None = None
        self._stop = threading.Event()
        self._connected = threading.Event()
        self._first_book = threading.Event()
        self.last_error: str = ""
        self.message_count = 0
        self._window_started = time.monotonic()
        self._ofi_signed_usd: dict[str, float] = defaultdict(float)
        self._ofi_gross_usd: dict[str, float] = defaultdict(float)
        self._buy_trade_usd: dict[str, float] = defaultdict(float)
        self._sell_trade_usd: dict[str, float] = defaultdict(float)
        self._last_trade_id: dict[str, int] = {}
        self._trade_gap_count: dict[str, int] = defaultdict(int)

    @property
    def connected(self) -> bool:
        return self._connected.is_set()

    def _on_open(self, ws) -> None:
        self._connected.set()
        ws.send(
            json.dumps(
                {
                    "type": "subscribe",
                    "product_ids": list(self.products),
                    "channels": ["level2_batch", "matches", "heartbeat"],
                }
            )
        )

    def _on_error(self, _ws, error) -> None:
        self.last_error = str(error)

    def _on_close(self, _ws, _status_code, _message) -> None:
        self._connected.clear()

    def _on_message(self, _ws, message: str) -> None:
        data = json.loads(message)
        product = data.get("product_id")
        self.message_count += 1
        if not product:
            return
        msg_type = data.get("type")
        with self.lock:
            if msg_type == "snapshot":
                self.bids[product] = {float(p): float(s) for p, s in data.get("bids", [])}
                self.asks[product] = {float(p): float(s) for p, s in data.get("asks", [])}
                if self.bids[product] and self.asks[product]:
                    self._first_book.set()
            elif msg_type == "l2update":
                for side, p, s in data.get("changes", []):
                    book = self.bids[product] if side == "buy" else self.asks[product]
                    price = float(p)
                    size = float(s)
                    previous = float(book.get(price, 0.0))
                    delta_notional = price * (size - previous)
                    # Positive = bid liquidity added / ask liquidity removed.
                    signed = delta_notional if side == "buy" else -delta_notional
                    self._ofi_signed_usd[product] += signed
                    self._ofi_gross_usd[product] += abs(delta_notional)
                    if size == 0:
                        book.pop(price, None)
                    else:
                        book[price] = size
            elif msg_type in {"match", "last_match"}:
                trade_id_raw = data.get("trade_id")
                if trade_id_raw is not None:
                    try:
                        trade_id = int(trade_id_raw)
                        previous_id = self._last_trade_id.get(product)
                        # `last_match` is the subscription bootstrap marker. It
                        # seeds the sequence but is not counted as interval flow.
                        if previous_id is not None and msg_type == "match" and trade_id > previous_id + 1:
                            self._trade_gap_count[product] += trade_id - previous_id - 1
                        self._last_trade_id[product] = trade_id
                    except (TypeError, ValueError):
                        pass
                if msg_type == "last_match":
                    return
                price = float(data.get("price") or 0)
                size = float(data.get("size") or 0)
                notional = price * size
                # Coinbase Exchange match.side is the maker side. Maker sell means
                # the aggressor/taker bought, therefore positive buy flow.
                maker_side = str(data.get("side") or "").lower()
                if maker_side == "sell":
                    self._buy_trade_usd[product] += notional
                elif maker_side == "buy":
                    self._sell_trade_usd[product] += notional

    def wait_until_ready(self, timeout: float = 15.0) -> bool:
        return self._first_book.wait(timeout)

    def metrics(self, product: str, *, reset_flow: bool = False) -> BookMetrics | None:
        with self.lock:
            if not self.bids[product] or not self.asks[product]:
                return None
            bids = sorted(self.bids[product].items(), reverse=True)[: self.depth_levels]
            asks = sorted(self.asks[product].items())[: self.depth_levels]
            best_bid, bid_size = bids[0]
            best_ask, ask_size = asks[0]
            mid = (best_bid + best_ask) / 2
            bid_depth = sum(p * s for p, s in bids)
            ask_depth = sum(p * s for p, s in asks)
            total = bid_depth + ask_depth
            imbalance = (bid_depth - ask_depth) / total if total else 0.0
            micro = (best_ask * bid_size + best_bid * ask_size) / max(bid_size + ask_size, 1e-9)
            gross_ofi = self._ofi_gross_usd[product]
            ofi = self._ofi_signed_usd[product] / gross_ofi if gross_ofi else 0.0
            buy_trade = self._buy_trade_usd[product]
            sell_trade = self._sell_trade_usd[product]
            trade_total = buy_trade + sell_trade
            trade_imbalance = (buy_trade - sell_trade) / trade_total if trade_total else 0.0
            sample_window_seconds = max(1, int(time.monotonic() - self._window_started))
            metric = BookMetrics(
                product=product,
                ts=datetime.now(timezone.utc).isoformat(),
                spread_bps=(best_ask - best_bid) / mid * 10000,
                bid_depth_usd=bid_depth,
                ask_depth_usd=ask_depth,
                imbalance=imbalance,
                microprice=micro,
                ofi=ofi,
                trade_imbalance=trade_imbalance,
                trade_notional_usd=trade_total,
                trade_gap_count=self._trade_gap_count[product],
                sample_window_seconds=sample_window_seconds,
            )
            if reset_flow:
                self._ofi_signed_usd[product] = 0.0
                self._ofi_gross_usd[product] = 0.0
                self._buy_trade_usd[product] = 0.0
                self._sell_trade_usd[product] = 0.0
                self._trade_gap_count[product] = 0
        if reset_flow:
            self._window_started = time.monotonic()
        return metric

    def run(self, duration_seconds: int, on_snapshot=None, snapshot_every: int = 60) -> None:
        self._stop.clear()
        self._window_started = time.monotonic()
        self.ws = websocket.WebSocketApp(
            self.URL,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        thread = threading.Thread(
            target=self.ws.run_forever,
            kwargs={"ping_interval": 20, "ping_timeout": 10},
            daemon=True,
        )
        thread.start()
        started = time.monotonic()
        next_snapshot = started + max(1, snapshot_every)
        try:
            if not self.wait_until_ready(min(15.0, max(3.0, duration_seconds / 2))):
                raise RuntimeError(self.last_error or "Coinbase realtime order book snapshot alınamadı.")
            while time.monotonic() - started < duration_seconds and not self._stop.wait(0.25):
                if on_snapshot and time.monotonic() >= next_snapshot:
                    for product in self.products:
                        metric = self.metrics(product, reset_flow=True)
                        if metric:
                            on_snapshot(metric)
                    next_snapshot = time.monotonic() + max(1, snapshot_every)
            # Always emit a final snapshot, even in a short smoke test.
            if on_snapshot:
                for product in self.products:
                    metric = self.metrics(product, reset_flow=True)
                    if metric:
                        on_snapshot(metric)
        finally:
            if self.ws:
                self.ws.close()
            thread.join(timeout=5)

    def stop(self) -> None:
        self._stop.set()
        if self.ws:
            self.ws.close()
