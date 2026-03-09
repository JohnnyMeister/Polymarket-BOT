import logging
from config.settings import settings
from engine.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Enforces risk limits: max exposure per market/strategy, 
    max total capital, and kill switch logic.
    """
    def __init__(self, execution_engine: ExecutionEngine):
        self.execution = execution_engine
        self.kill_switch_active = False

    def check_order_allowed(self, asset_id: str, size: float, price: float, strategy_id: str) -> bool:
        """Validate an order against all risk thresholds before placement."""
        if self.kill_switch_active:
            logger.warning(f"[{strategy_id}] Kill switch is active. Order rejected.")
            return False
            
        order_cost = size * price
        
        # Check Total Capital Limit
        if self.execution.total_capital_used + order_cost > settings.MAX_TOTAL_CAPITAL:
            logger.warning(f"[{strategy_id}] Total capital limit reached ({settings.MAX_TOTAL_CAPITAL}). Order rejected.")
            return False
            
        # Check Strategy Capital Limit
        current_strategy_cap = self.execution.get_strategy_capital(strategy_id)
        if current_strategy_cap + order_cost > settings.MAX_EXPOSURE_PER_STRATEGY:
            logger.warning(f"[{strategy_id}] Strategy exposure limit reached ({settings.MAX_EXPOSURE_PER_STRATEGY}). Order rejected.")
            return False

        # Market-specific limit (simplified logic per asset)
        current_pos = self.execution.get_strategy_position(strategy_id, asset_id)
        if (abs(current_pos) * price) + order_cost > settings.MAX_EXPOSURE_PER_MARKET:
            logger.warning(f"[{strategy_id}] Market exposure limit reached for {asset_id}. Order rejected.")
            return False
            
        return True

    def update_pnl(self, total_pnl: float):
        """Check kill switch based on global or strategy PNL."""
        if total_pnl <= settings.KILL_SWITCH_LOSS_THRESHOLD:
            if not self.kill_switch_active:
                logger.critical(f"KILL SWITCH ACTIVATED! Losses ({total_pnl}) exceeded threshold ({settings.KILL_SWITCH_LOSS_THRESHOLD})")
                self.kill_switch_active = True
                # Here you would typically also trigger a "Cancel All Orders" command 
                # to the execution engine to liquidate/halt all trading.
