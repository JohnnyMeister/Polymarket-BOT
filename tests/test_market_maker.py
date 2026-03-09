import pytest
import asyncio
from strategies.market_maker import MarketMakerStrategy, black_scholes_binary_call

class MockExecutionEngine:
    def __init__(self):
        self.orders = []
        
    async def place_order(self, asset_id, side, price, size, strategy_id):
        self.orders.append((asset_id, side, price, size, strategy_id))
        
    def get_strategy_position(self, *args, **kwargs):
        return 0.0 # Zero inventory for basic test

class MockRiskManager:
    def check_order_allowed(self, *args, **kwargs):
        return True

class MockStatsEngine:
    def record_trade(self, *args, **kwargs):
        pass

def test_black_scholes_binary_call():
    # ITM
    p_itm = black_scholes_binary_call(101000, 100000, 0.01, 0.0, 0.1)
    assert p_itm > 0.5
    
    # OTM
    p_otm = black_scholes_binary_call(99000, 100000, 0.01, 0.0, 0.1)
    assert p_otm < 0.5

@pytest.mark.asyncio
async def test_market_maker_quotes():
    execution = MockExecutionEngine()
    risk = MockRiskManager()
    stats = MockStatsEngine()
    
    strategy = MarketMakerStrategy(execution, risk, stats)
    
    # Set BTC Price to exactly Strike with some volatility
    await strategy.on_btc_update(100000.0, 0.2)
    
    # Expect fair prob to be around 0.5, quotes slightly below (bid) and above (ask)
    await strategy.on_book_update("BTC_100K_15m", {}, strike_price=100000.0, time_to_expiry_years=0.01)
    
    assert len(execution.orders) == 2
    # Expect roughly Fair: ~0.45-0.55 depending on drift logic, but primarily we want a bid and ask setup
    bids = [o for o in execution.orders if o[0].endswith("_YES")] # Buy YES = Bid
    asks = [o for o in execution.orders if o[0].endswith("_NO")]  # Buy NO = Sell YES = Ask

    assert len(bids) == 1
    assert len(asks) == 1
    
    # Spread check (base spread is 0.04)
    # The bid is YES price. 
    # The ask is 1 - NO price (since NO represents the other side)
    ask_implied = 1.0 - asks[0][2]
    bid_implied = bids[0][2]
    
    assert round(ask_implied - bid_implied, 2) == 0.04
