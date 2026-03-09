import pytest
from engine.execution_engine import ExecutionEngine
from engine.risk_manager import RiskManager
from config.settings import settings

@pytest.fixture
def risk_system():
    execution = ExecutionEngine()
    manager = RiskManager(execution)
    return execution, manager

def test_risk_manager_allows_valid_order(risk_system):
    execution, manager = risk_system
    
    # Simple order well within limits
    allowed = manager.check_order_allowed("BTC_100K_15m_1000", size=100.0, price=0.5, strategy_id="test_strat")
    assert allowed is True

def test_risk_manager_blocks_market_limit(risk_system):
    execution, manager = risk_system
    
    # Exceed market limit (MAX_EXPOSURE_PER_MARKET defaults to 1000)
    allowed = manager.check_order_allowed("BTC_100K_15m_1000", size=3000.0, price=0.5, strategy_id="test_strat")
    assert allowed is False

def test_risk_manager_kill_switch(risk_system):
    execution, manager = risk_system
    
    # Trigger PNL below threshold (KILL_SWITCH_LOSS_THRESHOLD defaults to -500)
    manager.update_pnl(-600.0)
    
    # Order should be rejected because kill switch is active
    allowed = manager.check_order_allowed("BTC_100K_15m_1000", size=100.0, price=0.5, strategy_id="test_strat")
    assert allowed is False
    assert manager.kill_switch_active is True
