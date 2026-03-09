import logging
from typing import Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class TemporalArbStrategy:
    """
    Strategy 2 — Temporal arbitrage
    Compare markets with the same strike price but different timeframes (5m vs 15m).
    Exploit violations of probability monotonicity: P(15m) should be >= P(5m).
    """
    def __init__(self, execution_engine, risk_manager, stats_engine):
        self.strategy_id = "temporal_arb"
        self.execution = execution_engine
        self.risk = risk_manager
        self.stats = stats_engine
        
        # Maintain latest P(YES) ask prices for markets
        self.market_prices: Dict[str, float] = {}
        self.min_violation_threshold = 0.03 # Require at least a 3% violation to arb

    async def on_book_update(self, asset_id: str, book: Dict[str, Any]):
        yes_ask = book.get("yes_ask", None)
        if yes_ask is None:
            return
            
        self.market_prices[asset_id] = yes_ask
        
        # In a real system you'd have an external mapping of 5m -> 15m markets
        # We simulate the cross-check using string replacement conventions
        if "5m" in asset_id:
            market_15m = asset_id.replace("5m", "15m")
            if market_15m in self.market_prices:
                await self.check_arbitrage(asset_id, market_15m)
                
        elif "15m" in asset_id:
            market_5m = asset_id.replace("15m", "5m")
            if market_5m in self.market_prices:
                await self.check_arbitrage(market_5m, asset_id)
                
    async def check_arbitrage(self, market_5m: str, market_15m: str):
        p_5m = self.market_prices.get(market_5m)
        p_15m = self.market_prices.get(market_15m)
        
        if p_5m is None or p_15m is None:
            return
            
        # P(15m) >= P(5m) strictly must hold. 
        # If P(5m) > P(15m) + threshold, Arb!
        # Sell 5m (Buy NO) and Buy 15m (Buy YES)
        if p_5m > p_15m + self.min_violation_threshold:
            logger.info(f"[{self.strategy_id}] Temporal Arb! 5m: {p_5m} > 15m: {p_15m}")
            
            trade_size = 50 # Fixed trade size instance
            p_5m_no = 1.0 - p_5m # Approximation of NO price (buy NO)
            
            if self.risk.check_order_allowed(market_5m, trade_size, p_5m_no, self.strategy_id) and \
               self.risk.check_order_allowed(market_15m, trade_size, p_15m, self.strategy_id):
               
                await asyncio.gather(
                    self.execution.place_order(f"{market_5m}_NO", "BUY", round(p_5m_no, 3), trade_size, self.strategy_id),
                    self.execution.place_order(f"{market_15m}_YES", "BUY", p_15m, trade_size, self.strategy_id)
                )
                
                # Record to stats
                combined_cost = (p_5m_no + p_15m) * trade_size
                # Note: Profit is unpredictable until market resolution. Log as trade executed.
                self.stats.record_trade(self.strategy_id, profit=0.0, capital_used=combined_cost)
