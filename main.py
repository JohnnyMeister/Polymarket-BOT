import asyncio
import logging
import signal
import sys
from config.settings import settings
from data.market_data import MarketDataEngine
from data.btc_feed import BTCFeed
from engine.execution_engine import ExecutionEngine
from engine.risk_manager import RiskManager
from analytics.stats_engine import global_stats_engine, start_dashboard
from strategies.intra_market_arb import IntraMarketArbStrategy
from strategies.temporal_arb import TemporalArbStrategy
from strategies.market_maker import MarketMakerStrategy

# Setup base logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def shutdown(loop, signal=None):
    """Cleanup tasks tied to the service's shutdown."""
    if signal:
        logger.info(f"Received exit signal {signal.name}...")
    
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    
    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    await asyncio.gather(*tasks, return_exceptions=True)
    loop.stop()

class TradingBotOrchestrator:
    def __init__(self):
        # Engines
        self.market_data = MarketDataEngine()
        self.btc_feed = BTCFeed()
        self.execution = ExecutionEngine()
        self.risk_manager = RiskManager(self.execution)
        self.stats = global_stats_engine
        
        # Strategies
        self.intra_arb = IntraMarketArbStrategy(self.execution, self.risk_manager, self.stats)
        self.temporal_arb = TemporalArbStrategy(self.execution, self.risk_manager, self.stats)
        self.market_maker = MarketMakerStrategy(self.execution, self.risk_manager, self.stats)
        
        # Pre-configure markets to watch
        # In a real environment, you'd pull active markets dynamically from Polymarket API
        self.target_markets = [
            "BTC_100K_15m_1000",
            "BTC_100K_5m_1000",
            "BTC_101K_15m_1000",
            "BTC_101K_5m_1000"
        ]
        self.market_data.subscribe_markets(self.target_markets)

    def setup_routing(self):
        """Map data feed events to strategy callbacks."""
        
        # Route BTC Price updates
        async def on_btc_update(mid_price: float, volatility: float):
            await self.market_maker.on_btc_update(mid_price, volatility)
            
        self.btc_feed.register_callback(on_btc_update)
        
        # Route Polymarket updates
        async def on_pm_update(event_type: str, asset_id: str, data: dict):
            if event_type == "book_update":
                await self.intra_arb.on_book_update(asset_id, data)
                await self.temporal_arb.on_book_update(asset_id, data)
                
                # For Market Maker we need generic strike/expiry metadata
                # Hardcoded proxy logic mapping asset string -> meta
                strike = 100000.0 if "100K" in asset_id else 101000.0 
                expiry_years = (15.0 / (60*24*365)) if "15m" in asset_id else (5.0 / (60*24*365))
                
                await self.market_maker.on_book_update(asset_id, data, strike, expiry_years)
                
        self.market_data.register_callback(on_pm_update)

    async def run(self):
        self.setup_routing()
        
        logger.info("Starting up Trading Bot Engines...")
        
        # Run loops concurrently
        await asyncio.gather(
            self.btc_feed.run(),
            self.market_data.run(),
            start_dashboard() # FastAPI metrics dashboard
        )

if __name__ == "__main__":
    bot = TradingBotOrchestrator()
    
    # Modern asyncio runtime handling
    async def main_loop():
        loop = asyncio.get_running_loop()
        
        # Only attach signal handlers if they exist (POSIX systems mostly)
        signals = []
        if sys.platform != "win32":
            signals = (getattr(signal, "SIGHUP", None), getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None))
            signals = [s for s in signals if s is not None]
            
            for s in signals:
                try:
                    loop.add_signal_handler(s, lambda s=s: asyncio.create_task(shutdown(loop, signal=s)))
                except NotImplementedError:
                    pass
        await bot.run()
                 
    try:
        asyncio.run(main_loop())
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    finally:
        logger.info("Successfully shutdown trading bot.")
