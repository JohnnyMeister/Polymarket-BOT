import asyncio
import json
import logging
import websockets
import numpy as np
from collections import deque
from config.settings import settings

logger = logging.getLogger(__name__)

class BTCFeed:
    """
    Connects to Binance websocket to get real-time BTC trades.
    Calculates mid price and short-term volatility.
    """
    def __init__(self):
        self.ws_url = settings.BINANCE_WS_URL
        self.mid_price: float = 0.0
        self.volatility: float = 0.0
        self._price_history = deque(maxlen=300) # keep last 300 price updates for vol
        self._callbacks = []

    def register_callback(self, callback):
        """Register an async callback triggered on price update."""
        self._callbacks.append(callback)

    async def _handle_message(self, message: str):
        data = json.loads(message)
        # Assuming aggTrade stream: { 'p': price, ... }
        if 'p' in data:
            price = float(data['p'])
            self.mid_price = price
            self._price_history.append(price)
            
            if len(self._price_history) >= 2:
                # simple volatility calculation (std dev of prices)
                self.volatility = float(np.std(self._price_history))
            
            for cb in self._callbacks:
                await cb(self.mid_price, self.volatility)

    async def run(self):
        while True:
            try:
                logger.info(f"Connecting to Binance WS: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    logger.info("Connected to Binance WS")
                    async for message in ws:
                        await self._handle_message(message)
            except Exception as e:
                logger.error(f"Binance WS error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
