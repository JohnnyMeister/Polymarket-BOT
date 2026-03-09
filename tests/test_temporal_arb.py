import pytest
import asyncio
from strategies.temporal_arb import TemporalArbStrategy

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
async def test_temporal_arb_monotonicity_violation():
    execution = MockExecutionEngine()
    risk = MockRiskManager()
    stats = MockStatsEngine()
    
    strategy = TemporalArbStrategy(execution, risk, stats)
    
    # Normal case: P(15m) >= P(5m)
    # 5m P(YES) = 0.4, 15m P(YES) = 0.5
    await strategy.on_book_update("BTC_100K_15m_1000", {"yes_ask": 0.5})
    await strategy.on_book_update("BTC_100K_5m_1000", {"yes_ask": 0.4})
    
    assert len(execution.orders) == 0
    
    # Violation case: P(5m) > P(15m) + threshold
    # 5m P(YES) = 0.6, 15m P(YES) = 0.5
    # threshold is 0.03
    await strategy.on_book_update("BTC_100K_5m_1000", {"yes_ask": 0.6})
    
    assert len(execution.orders) == 2
    # Should Buy 5m NO (Sell 5m YES) and Buy 15m YES
    assert any("5m" in o[0] and "NO" in o[0] for o in execution.orders)
    assert any("15m" in o[0] and "YES" in o[0] for o in execution.orders)

