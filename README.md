# Polymarket BTC Trading Bot

A high-performance asynchronous bot for Polymarket prediction markets focused on short-term BTC markets (5m and 15m).

## Overview
This bot features a modular event-driven architecture that supports multiple strategies simultaneously:
1. **Intra-market Arbitrage**: Exploits (YES + NO < 1) inefficiencies.
2. **Temporal Arbitrage**: Exploits P(15m) < P(5m) monotonicity violations.
3. **Market Making**: Quotes bids and asks around fair probability with inventory control. 

## Requirements
- Python 3.10+
- `pip install -r requirements.txt`

## Configuration
1. Copy `.env.example` to `.env`
2. Fill out the environment variables in `.env` with your API keys.

## Running the Bot
```bash
python main.py
```

## Dashboard
The bot includes a FastAPI dashboard for tracking performance and statistics across strategies.
Visit `http://localhost:8000/docs` while the bot is running to see API docs.
