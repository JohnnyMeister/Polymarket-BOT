import asyncio
import json
import logging
import websockets
from typing import Dict, Any, List
from config.settings import settings

logger = logging.getLogger(__name__)

class MarketDataEngine:
    """
    Connects to Polymarket websocket to get live orderbooks and trades.
    """
    def __init__(self):
        self.ws_url = settings.POLYMARKET_WS_HOST
        self.orderbooks: Dict[str, Any] = {}
        self.active_markets: List[str] = [] # list of asset IDs
        self._callbacks = []

    def register_callback(self, callback):
        """Register an async callback triggered on orderbook/trade updates."""
        self._callbacks.append(callback)

    def subscribe_markets(self, asset_ids: List[str]):
        """Queue markets to subscribe to when connected."""
        for asset in asset_ids:
            if asset not in self.active_markets:
                self.active_markets.append(asset)
                self.orderbooks[asset] = {"bids": [], "asks": []}

    async def _handle_message(self, message: str):
        data = json.loads(message)
        
        # Depending on Polymarket CLOB WS schema, extract event type
        event_type = data.get("event")
        asset_id = data.get("asset_id")
        
        if event_type == "book":
            # Just an example schema handling, adapt according to actual Polymarket ws schema
            self.orderbooks[asset_id] = {
                "bids": data.get("bids", []),
                "asks": data.get("asks", [])
            }
            # Trigger callbacks
            for cb in self._callbacks:
                await cb("book_update", asset_id, self.orderbooks[asset_id])
                
        elif event_type == "trade":
            for cb in self._callbacks:
                await cb("trade", data.get("asset_id"), data)

    async def run(self):
        if not self.active_markets:
            logger.warning("No markets to subscribe to via WS.")
            # Typically we still connect or we wait, but let's just connect and wait.
            # return

        while True:
            try:
                logger.info(f"Connecting to Polymarket WS: {self.ws_url}")
                async with websockets.connect(self.ws_url) as ws:
                    logger.info("Connected to Polymarket WS")
                    
                    if self.active_markets:
                        # Send subscription message for orderbooks
                        sub_msg = {
                            "assets": self.active_markets,
                            "type": "market"
                        }
                        await ws.send(json.dumps(sub_msg))
                    
                    async for message in ws:
                        await self._handle_message(message)
            except Exception as e:
                logger.error(f"Polymarket WS error: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)
