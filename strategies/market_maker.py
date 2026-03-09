import logging
import asyncio
import numpy as np
import scipy.stats as si
from typing import Dict, Any

logger = logging.getLogger(__name__)

def black_scholes_binary_call(S, K, T, r, sigma):
    """
    Calculates fair probability of asset closing above strike (binary call).
    S: current underlying price
    K: strike level
    T: time to expiry in years
    r: risk-free rate
    sigma: volatility
    """
    if T <= 0 or sigma <= 0:
        return 1.0 if S > K else 0.0
    d2 = (np.log(S / K) + (r - 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return si.norm.cdf(d2)

class MarketMakerStrategy:
    """
    Strategy 3 — Market making
    Calculates fair probability using: BTC price, strike, time, volatility.
    Places bid/ask orders around fair value to capture spread.
    Includes inventory control to avoid excessive exposure.
    """
    def __init__(self, execution_engine, risk_manager, stats_engine):
        self.strategy_id = "market_maker"
        self.execution = execution_engine
        self.risk = risk_manager
        self.stats = stats_engine
        
        self.current_btc_price = 0.0
        self.current_vol = 0.1 # Annualized proxy
        self.base_spread = 0.04 # 4% total spread
        self.inventory_risk_aversion = 0.005 # Determines how fast spread skews based on inventory

    async def on_btc_update(self, mid_price: float, volatility: float):
        self.current_btc_price = mid_price
        
        # Convert short-term tick volatility to a reasonable BS input scale if needed.
        # We keep it simple here.
        if volatility > 0:
            self.current_vol = max(volatility, 0.05)
        
    async def on_book_update(self, asset_id: str, book: Dict[str, Any], strike_price: float, time_to_expiry_years: float):
        if self.current_btc_price <= 0:
            return
            
        # Calculate Fair Value P(YES)
        fair_prob = black_scholes_binary_call(
            S=self.current_btc_price, 
            K=strike_price, 
            T=max(time_to_expiry_years, 0.0001), 
            r=0.0, 
            sigma=self.current_vol
        )
        
        # Inventory control calculation
        # Positive inventory = long YES. We'll skew heavily to sell YES (buy NO) to balance.
        inventory = self.execution.get_strategy_position(self.strategy_id, f"{asset_id}_YES")
        
        inventory_skew = -inventory * self.inventory_risk_aversion 
        
        adjusted_fair = max(0.01, min(0.99, fair_prob + inventory_skew))
        
        bid_price = round(adjusted_fair - (self.base_spread / 2), 3) # Market making buy YES
        ask_price = round(adjusted_fair + (self.base_spread / 2), 3) # Market making sell YES (equivalent to buy NO @ 1-ask)
        
        trade_size = 20 # Quoting size in standard lots/USD
        
        logger.debug(f"[{self.strategy_id}] {asset_id} Fair: {fair_prob:.2f}, Bid: {bid_price}, Ask: {ask_price}, Inv: {inventory}")
        
        tasks = []
        # Place orders if risk limits allow
        if bid_price > 0.01 and self.risk.check_order_allowed(asset_id, trade_size, bid_price, self.strategy_id):
             tasks.append(
                 self.execution.place_order(f"{asset_id}_YES", "BUY", bid_price, trade_size, self.strategy_id)
             )
             
        if ask_price < 0.99 and self.risk.check_order_allowed(asset_id, trade_size, 1-ask_price, self.strategy_id):
             # To sell YES we place a BUY on the NO token
             tasks.append(
                 self.execution.place_order(f"{asset_id}_NO", "BUY", round(1-ask_price, 3), trade_size, self.strategy_id)
             )
             
        if tasks:
            await asyncio.gather(*tasks)
            # Log quoted volume as an internal metric
            self.stats.record_trade(self.strategy_id, profit=0.0, capital_used=trade_size * len(tasks))
