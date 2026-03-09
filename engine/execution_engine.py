import asyncio
import logging
from typing import Dict, List, Optional
from config.settings import settings

logger = logging.getLogger(__name__)

class Order:
    def __init__(self, asset_id: str, side: str, price: float, size: float, strategy_id: str):
        self.order_id: Optional[str] = None
        self.asset_id = asset_id
        self.side = side  # "BUY" or "SELL"
        self.price = price
        self.size = size
        self.strategy_id = strategy_id
        self.status = "PENDING"
        self.filled_size = 0.0

class ExecutionEngine:
    """
    Responsible for order placement, cancellation, updates, and position tracking.
    Attributes trades to specific strategy_ids.
    """
    def __init__(self):
        # In a real application, initialize Polymarket CLOB client here
        self.active_orders: Dict[str, Order] = {}
        self.positions: Dict[str, Dict[str, float]] = {} # strategy_id -> {asset_id: size}
        self.strategy_capital: Dict[str, float] = {}
        self.total_capital_used: float = 0.0

    async def place_order(self, asset_id: str, side: str, price: float, size: float, strategy_id: str) -> Optional[Order]:
        """Place an order with Polymarket."""
        logger.info(f"[{strategy_id}] Placing {side} {size} @ {price} for {asset_id}")
        order = Order(asset_id, side, price, size, strategy_id)
        
        # Mocking API latency
        await asyncio.sleep(0.05) 
        order.order_id = f"mock_id_{len(self.active_orders)}_{id(order)}"
        order.status = "OPEN"
        
        self.active_orders[order.order_id] = order
        return order

    async def cancel_order(self, order_id: str):
        """Cancel an active order."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            logger.info(f"[{order.strategy_id}] Cancelling order {order_id}")
            # Mocking API latency
            await asyncio.sleep(0.05)
            order.status = "CANCELED"
            del self.active_orders[order_id]

    def update_position(self, strategy_id: str, asset_id: str, size_delta: float, price: float):
        """Update tracked position when an order fills."""
        if strategy_id not in self.positions:
            self.positions[strategy_id] = {}
            self.strategy_capital[strategy_id] = 0.0

        current_size = self.positions[strategy_id].get(asset_id, 0.0)
        self.positions[strategy_id][asset_id] = current_size + size_delta
        
        # Approximate capital mapping (cost of the position)
        cost = size_delta * price
        self.strategy_capital[strategy_id] += abs(cost)
        self.total_capital_used += abs(cost)
        
    def get_strategy_position(self, strategy_id: str, asset_id: str) -> float:
        return self.positions.get(strategy_id, {}).get(asset_id, 0.0)

    def get_strategy_capital(self, strategy_id: str) -> float:
        return self.strategy_capital.get(strategy_id, 0.0)
