# KIS AI Trader

Multi-agent AI-powered stock trading system using Korea Investment Securities (KIS) API.

## Overview

KIS AI Trader is an intelligent trading system that leverages AI agents for automated stock analysis and portfolio management. The system consists of 5 specialized AI agents working together through an event-driven architecture.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Main Coordinator                          │
│                    (Daily Trading Cycle)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐  ┌─────────────┐  ┌──────────────────┐
│   Collector   │  │   Analyst   │  │   Strategist     │
│    Agent      │  │    Agent    │  │     Agent        │
│               │  │             │  │                  │
│ - KIS Data    │  │ - Technical │  │ - Momentum       │
│ - DART        │  │ - Fundamental│ │ - Value          │
│ - News        │  │ - Sentiment │  │ - Mean Reversion │
│ - BOK/FRED    │  │             │  │ - Composite      │
└───────────────┘  └─────────────┘  └──────────────────┘
        │                 │                 │
        └─────────────────┼─────────────────┘
                          ▼
              ┌───────────────────────┐
              │  Portfolio Manager    │
              │       Agent            │
              │                        │
              │ - Position Sizing      │
              │ - Rebalancing          │
              └───────────┬────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │      CIO Agent        │
              │                        │
              │ - Final Decision      │
              │ - Emergency Handling   │
              └───────────┬────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │      Risk Guard       │
              │                        │
              │ - Pre-trade Validation│
              │ - Circuit Breaker     │
              │ - Position Limits     │
              └───────────────────────┘
```

### AI Agents

| Agent | Responsibility |
|-------|----------------|
| **Collector** | Gather market data from KIS, DART, News, BOK, FRED |
| **Analyst** | Technical, Fundamental, and Sentiment analysis |
| **Strategist** | Generate trading signals using multiple strategies |
| **Portfolio Manager** | Position sizing and portfolio rebalancing |
| **CIO** | Final decision making and emergency handling |

## KIS API Setup

### 1. Apply for KIS Open API

1. **Apply on KIS Developers Portal**: https://apiportal.koreainvestment.com
2. Get **APP Key** and **APP Secret** (for both paper and live trading)
3. Apply for **Paper Trading** (virtual account)

### 2. Environment Variables

Create `.env` file in project root:

```bash
# KIS API Credentials
KIS_APP_KEY=your_paper_app_key        # 36 characters
KIS_APP_SECRET=your_paper_app_secret   # 180 characters
KIS_ACCOUNT_NO=12345678-01            # Account number (8 digits - 2 digits)
KIS_HTS_ID=your_hts_id                # HTS Login ID

# Database
DB_PASSWORD=your_db_password

# Notifications (Telegram)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# AI (OpenAI)
OPENAI_API_KEY=your_openai_key
```

### 3. Configuration

Edit `config/settings.yaml`:

```yaml
app:
  name: "KIS AI Trader"
  env: "paper"  # "paper" or "live"
  log_level: "INFO"
  timezone: "Asia/Seoul"

kis:
  paper:
    base_url: "https://openapivts.koreainvestment.com:29443"
    websocket_url: "ws://ops.koreainvestment.com:31000"
  live:
    base_url: "https://openapi.koreainvestment.com:9443"
    websocket_url: "ws://ops.koreainvestment.com:21000"
```

## Installation

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/SungminKo-smko/kis-ai-trader
cd kis-ai-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your credentials
```

### Docker Setup

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Usage

### Running the Trading System

```bash
# Start daily trading cycle
python -m src.main_coordinator

# Or with custom date
python -m src.main_coordinator --date 2026-02-23
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_collector_agent.py

# Run with coverage
pytest --cov=src tests/
```

## KIS API Usage Examples

### Using KISClient

```python
from broker.kis_client import KISClient, create_kis_client
from decimal import Decimal

# Create client
client = create_kis_client(
    app_key="your_app_key",
    app_secret="your_app_secret",
    account_no="12345678-01",
    is_paper=True,  # True for paper trading
    hts_id="your_hts_id",
)

# Get current price
price = client.get_current_price("005930")  # Samsung Electronics
print(f"Price: {price}")

# Get quote with indicators
quote = client.get_quote("005930")
print(f"PER: {quote['indicator']['per']}")
print(f"PBR: {quote['indicator']['pbr']}")

# Get OHLCV chart
chart = client.get_chart("005930", period="1d")
for bar in chart:
    print(f"{bar['time']}: O={bar['open']} H={bar['high']} L={bar['low']} C={bar['close']}")

# Get account balance
balance = client.get_balance()
print(f"Total assets: {balance['current_amount']}")

# Place buy order
order = client.buy("005930", quantity=10)  # Buy 10 shares at market price
# or with limit price
order = client.buy("005930", quantity=10, price=Decimal("70000"))

# Place sell order
order = client.sell("005930", quantity=10)

# Cancel order
client.cancel_order(order_number="123456")
```

### Supported Markets

| Market Code | Description |
|-------------|-------------|
| KRX | Korea Exchange (KOSPI) |
| KOSDAQ | KOSDAQ |
| NASDAQ | NASDAQ |
| NYSE | New York Stock Exchange |
| AMEX | American Stock Exchange |
| TYO | Tokyo Stock Exchange |
| HKG | Hong Kong Stock Exchange |

### Order Conditions

| Condition | Description |
|-----------|-------------|
| None | Regular order |
| "best" | Best price (Best Limit) |
| "condition" | Conditional order |
| "extended" | Extended hours trading |

## Project Structure

```
kis-ai-trader/
├── config/
│   ├── settings.yaml
│   └── risk.yaml
├── src/
│   ├── agents/
│   │   ├── collector/
│   │   ├── analyst/
│   │   ├── strategist/
│   │   ├── portfolio/
│   │   └── cio/
│   ├── core/
│   │   ├── event_bus.py
│   │   └── config.py
│   ├── broker/
│   │   ├── kis_client.py
│   │   └── ...
│   ├── main_coordinator.py
│   └── risk_guard.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pytest.ini
└── README.md
```

## Development

### Code Style

- Type hints required for all functions
- Use `ruff` for linting
- Use `pyright` for type checking

```bash
# Lint code
ruff check src/

# Type check
pyright src/
```

### Adding New Strategies

1. Create new strategy class in `src/agents/strategist/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `generate_signal` method
4. Add to strategy registry

## References

- **KIS Developers Portal**: https://apiportal.koreainvestment.com
- **python-kis Library**: https://github.com/Soju06/python-kis
- **Official API Docs**: https://github.com/koreainvestment/open-trading-api

## License

MIT License
