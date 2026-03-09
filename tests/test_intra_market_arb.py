import pytest
import asyncio
from strategies.intra_market_arb import IntraMarketArbStrategy

class MockExecutionEngine:
    def __init__(self):
        self.orders = []
        
    async def place_order(self, asset_id, side, price, size, strategy_id):
        self.orders.append((asset_id, side, price, size, strategy_id))

class MockRiskManager:
    def check_order_allowed(self, *args, **kwargs):
        return True

class MockStatsEngine:
    def record_trade(self, *args, **kwargs):
        pass

@pytest.mark.asyncio
async def test_intra_market_arb_triggers():
    execution = MockExecutionEngine()
    risk = MockRiskManager()
    stats = MockStatsEngine()
    
    strategy = IntraMarketArbStrategy(execution, risk, stats)
    
    # Simulate book update where cost > 1 (No arb)
    await strategy.on_book_update("BTC_TEST", {"yes_ask": 0.60, "no_ask": 0.50})
    assert len(execution.orders) == 0
    
    # Simulate book update where cost < 1 - threshold 
    # Yes (0.40) + No (0.50) = 0.90 (cost) < 0.98
    await strategy.on_book_update("BTC_TEST", {"yes_ask": 0.40, "no_ask": 0.50})
    assert len(execution.orders) == 2
    
    # Validate order details
    assert any("BTC_TEST_YES" in o and 0.40 in o for o in execution.orders)
    assert any("BTC_TEST_NO" in o and 0.50 in o for o in execution.orders)
