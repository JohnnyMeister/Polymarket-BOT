import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from config.settings import settings
import asyncio
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

Base = declarative_base()

class TradeRecord(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    strategy_id = Column(String, index=True)
    profit = Column(Float)
    capital_used = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class StatsEngine:
    """
    Tracks performance per strategy including total trades, profit, ROI, win rate, 
    average expected value, max drawdown, and profit per dollar of liquidity.
    Persists data to SQLite via SQLAlchemy.
    """
    def __init__(self):
        # Database setup
        # For simplicity we default to SQLite
        self.engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # In-memory stats for fast querying
        self.stats = {}
        
    def record_trade(self, strategy_id: str, profit: float, capital_used: float = 0.0):
        with self.SessionLocal() as db:
            trade = TradeRecord(strategy_id=strategy_id, profit=profit, capital_used=capital_used)
            db.add(trade)
            db.commit()
            
        self._update_in_memory_stats(strategy_id, profit, capital_used)
        
    def _update_in_memory_stats(self, strategy_id: str, profit: float, capital_used: float):
        if strategy_id not in self.stats:
            self.stats[strategy_id] = {
                "total_trades": 0,
                "winning_trades": 0,
                "total_profit": 0.0,
                "total_capital_used": 0.0,
                "peak_profit": 0.0,
                "max_drawdown": 0.0,
            }
            
        s = self.stats[strategy_id]
        s["total_trades"] += 1
        if profit > 0:
            s["winning_trades"] += 1
            
        s["total_profit"] += profit
        s["total_capital_used"] += capital_used
        
        if s["total_profit"] > s["peak_profit"]:
            s["peak_profit"] = s["total_profit"]
            
        drawdown = s["peak_profit"] - s["total_profit"]
        if drawdown > s["max_drawdown"]:
            s["max_drawdown"] = drawdown

    def get_strategy_performance(self, strategy_id: str) -> dict:
        s = self.stats.get(strategy_id)
        if not s or s["total_trades"] == 0:
            return {}
            
        win_rate = s["winning_trades"] / s["total_trades"]
        roi = (s["total_profit"] / s["total_capital_used"]) if s["total_capital_used"] > 0 else 0.0
        avg_ev = s["total_profit"] / s["total_trades"]
        profit_per_dollar = (s["total_profit"] / s["total_capital_used"]) if s["total_capital_used"] > 0 else 0.0
        
        return {
            "strategy": strategy_id,
            "total_trades": s["total_trades"],
            "total_profit": round(s["total_profit"], 2),
            "roi_percent": round(roi * 100, 2),
            "win_rate_percent": round(win_rate * 100, 2),
            "average_ev": round(avg_ev, 4),
            "max_drawdown": round(s["max_drawdown"], 2),
            "profit_per_dollar_liquidity": round(profit_per_dollar, 4)
        }

    def get_all_performance(self):
        return {s_id: self.get_strategy_performance(s_id) for s_id in self.stats.keys()}

# Global stats engine instance to share with FastAPI endpoints
global_stats_engine = StatsEngine()

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

app = FastAPI(title="Polymarket BTC Bot Dashboard", description="Monitors strategy performance", lifespan=lifespan)

# Mount the static directory
dashboard_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
app.mount("/dashboard", StaticFiles(directory=dashboard_dir), name="dashboard")

@app.get("/")
def redirect_to_dashboard():
    with open(os.path.join(dashboard_dir, "index.html"), "r") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/v1/stats")
def get_stats():
    return global_stats_engine.get_all_performance()

@app.get("/api/v1/stats/{strategy_id}")
def get_strategy_stats(strategy_id: str):
    return global_stats_engine.get_strategy_performance(strategy_id)

async def start_dashboard():
    """Starts the FastAPI uvicorn server in the async loop."""
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()
