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

## Installation

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Local Development Setup

```bash
# Clone repository
git clone <repository-url>
cd kis-ai-trader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -e .

# Setup configuration
cp config/settings.example.yaml config/settings.yaml
cp config/risk.example.yaml config/risk.yaml

# Edit configuration files with your credentials
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

## Configuration

### settings.yaml

```yaml
app:
  name: "KIS AI Trader"
  env: "development"
  debug: true

kis:
  app_key: "your_app_key"
  app_secret: "your_app_secret"
  account_number: "your_account_number"
  is_demo: true  # Use demo account

database:
  host: "localhost"
  port: 5432
  name: "kis_trader"
  user: "postgres"
  password: "your_password"

redis:
  host: "localhost"
  port: 6379

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

### risk.yaml

```yaml
risk:
  max_position_size: 0.1       # 10% of portfolio per position
  max_total_leverage: 1.0        # No leverage
  max_sector_concentration: 0.3 # 30% per sector
  daily_loss_limit: 0.02        # 2% daily loss limit
  monthly_loss_limit: 0.05     # 5% monthly loss limit

circuit_breaker:
  enabled: true
  consecutive_losses: 3
  pause_duration_minutes: 60
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
│   ├── main_coordinator.py
│   └── risk_guard.py
├── tests/
├── docker-compose.yml
├── Dockerfile
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

## License

MIT License
