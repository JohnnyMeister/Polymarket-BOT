import logging
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

class IntraMarketArbStrategy:
    """
    Strategy 1 — Intra-market arbitrage
    Detect situations where: YES price + NO price < 1
    Execute simultaneous buy orders for both sides when profitable after fees.
    """
    def __init__(self, execution_engine, risk_manager, stats_engine):
        self.strategy_id = "intra_market_arb"
        self.execution = execution_engine
        self.risk = risk_manager
        self.stats = stats_engine
        self.min_profit_threshold = 0.02 # 2% profit margin

    async def on_book_update(self, asset_id: str, book: Dict[str, Any]):
        """
        Called when orderbook updates on a single market.
        Assumes book contains 'yes_ask' and 'no_ask' pricing.
        """
        # Polymarket typically uses distinct token IDs for YES and NO per condition.
        # Here we abstract it assuming the engine gives us combined market books.
        yes_ask = book.get("yes_ask")
        no_ask = book.get("no_ask")
        
        if yes_ask is None or no_ask is None:
            return
            
        total_cost = yes_ask + no_ask
        
        if total_cost < (1.0 - self.min_profit_threshold):
            profit_margin = 1.0 - total_cost
            logger.info(f"[{self.strategy_id}] Arbitrage opportunity found on {asset_id}! Cost: {total_cost:.3f}")
            
            trade_size = 100 # Standard fixed size (USD)
            
            # Risk check
            yes_allowed = self.risk.check_order_allowed(asset_id, trade_size, yes_ask, self.strategy_id)
            no_allowed = self.risk.check_order_allowed(asset_id, trade_size, no_ask, self.strategy_id)
            
            if yes_allowed and no_allowed:
                # Place simultaneous YES and NO buys
                # Real implementation references distinct YES and NO token IDs.
                await asyncio.gather(
                    self.execution.place_order(f"{asset_id}_YES", "BUY", yes_ask, trade_size, self.strategy_id),
                    self.execution.place_order(f"{asset_id}_NO", "BUY", no_ask, trade_size, self.strategy_id)
                )
                
                # Assume filled (mock), record stats
                self.stats.record_trade(self.strategy_id, profit=profit_margin * trade_size, capital_used=total_cost * trade_size)
