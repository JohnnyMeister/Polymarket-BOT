import asyncio
import logging
from engine.execution_engine import ExecutionEngine
from engine.risk_manager import RiskManager
from analytics.stats_engine import global_stats_engine
from strategies.intra_market_arb import IntraMarketArbStrategy
from strategies.temporal_arb import TemporalArbStrategy
from strategies.market_maker import MarketMakerStrategy

logging.basicConfig(level="INFO", format='%(message)s')
logger = logging.getLogger(__name__)

class Backtester:
    """
    Simulation environment for replaying historical or generated 
    market data through the strategies to assess performance offline.
    """
    def __init__(self):
        self.execution = ExecutionEngine()
        self.risk_manager = RiskManager(self.execution)
        self.stats = global_stats_engine
        
        self.intra_arb = IntraMarketArbStrategy(self.execution, self.risk_manager, self.stats)
        self.temporal_arb = TemporalArbStrategy(self.execution, self.risk_manager, self.stats)
        self.market_maker = MarketMakerStrategy(self.execution, self.risk_manager, self.stats)

    async def run_simulation(self):
        logger.info("Starting Backtest Simulation...")
        
        # 1. Simulate BTC Price Updates
        await self.market_maker.on_btc_update(mid_price=100000.0, volatility=0.15)
        
        # 2. Simulate Market Condition: Intra-Market Arb (YES + NO < 1)
        logger.info("\n--- Applying Intra-Market Arb Scenario ---")
        await self.intra_arb.on_book_update("BTC_100K_15m", {"yes_ask": 0.40, "no_ask": 0.50})
        
        # 3. Simulate Market Condition: Temporal Arb (P(15m) < P(5m))
        logger.info("\n--- Applying Temporal Arb Scenario ---")
        await self.temporal_arb.on_book_update("BTC_100K_15m_1000", {"yes_ask": 0.45})
        await self.temporal_arb.on_book_update("BTC_100K_5m_1000", {"yes_ask": 0.60})
        
        # 4. Simulate Market Condition: Market Making
        logger.info("\n--- Applying Market Maker Scenario ---")
        await self.market_maker.on_book_update("BTC_100K_15m_1000", {}, strike_price=100000.0, time_to_expiry_years=0.01)

        # 5. Summarize Results
        logger.info("\n--- Backtest Results ---")
        results = self.stats.get_all_performance()
        for strategy_id, perf in results.items():
            if perf:
                logger.info(f"{strategy_id.upper()}:")
                for k, v in perf.items():
                    if k != "strategy":
                         logger.info(f"  {k}: {v}")

if __name__ == "__main__":
    backtester = Backtester()
    asyncio.run(backtester.run_simulation())
