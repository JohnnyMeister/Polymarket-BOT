import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Polymarket API
    POLYMARKET_API_KEY: str = os.getenv("POLYMARKET_API_KEY", "")
    POLYMARKET_API_SECRET: str = os.getenv("POLYMARKET_API_SECRET", "")
    POLYMARKET_PASSPHRASE: str = os.getenv("POLYMARKET_PASSPHRASE", "")
    POLYMARKET_HOST: str = os.getenv("POLYMARKET_HOST", "https://clob.polymarket.com")
    POLYMARKET_WS_HOST: str = os.getenv("POLYMARKET_WS_HOST", "wss://ws-subscriptions-clob.polymarket.com/ws/market")
    
    # Binance API
    BINANCE_WS_URL: str = os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/btcusdt@aggTrade")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./polymarket_bot.db")
    
    # Application Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Risk Management Limits
    MAX_EXPOSURE_PER_MARKET: float = 1000.0  # max exposure (USD) per single market
    MAX_EXPOSURE_PER_STRATEGY: float = 5000.0 # max exposure (USD) per strategy
    MAX_TOTAL_CAPITAL: float = 10000.0 # max total capital to use across bot
    KILL_SWITCH_LOSS_THRESHOLD: float = -500.0 # automatically stop bot if losses reach this

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
