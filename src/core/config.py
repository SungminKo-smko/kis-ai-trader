from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    app_key: str = Field("", alias="KIS_APP_KEY")
    app_secret: str = Field("", alias="KIS_APP_SECRET")
    account_no: str = Field("", alias="KIS_ACCOUNT_NO")
    db_password: str = Field("", alias="DB_PASSWORD")
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")
    openai_api_key: str = Field("", alias="OPENAI_API_KEY")


class AppSettings(BaseSettings):
    name: str = "KIS AI Trader"
    env: str = "paper"
    log_level: str = "INFO"
    timezone: str = "Asia/Seoul"


class KISSettings(BaseSettings):
    paper_base_url: str = "https://openapivts.koreainvestment.com:29443"
    paper_websocket_url: str = "ws://ops.koreainvestment.com:31000"
    live_base_url: str = "https://openapi.koreainvestment.com:9443"
    live_websocket_url: str = "ws://ops.koreainvestment.com:21000"

    @property
    def base_url(self) -> str:
        from . import get_settings
        settings = get_settings()
        return self.live_base_url if settings.app.env == "live" else self.paper_base_url

    @property
    def websocket_url(self) -> str:
        from . import get_settings
        settings = get_settings()
        return self.live_websocket_url if settings.app.env == "live" else self.paper_websocket_url


class DatabaseSettings(BaseSettings):
    url: str = "postgresql+asyncpg://trader:password@localhost:5432/kis_trader"
    pool_size: int = 10
    max_overflow: int = 20


class RedisSettings(BaseSettings):
    url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 5


class SchedulerSettings(BaseSettings):
    daily_cycle_cron: str = "0 8 50 * * MON-FRI"
    data_collection_interval_minutes: int = 5
    portfolio_snapshot_cron: str = "0 16 0 * * MON-FRI"
    rebalance_check_cron: str = "0 9 0 * * MON-FRI"


class UniverseSettings(BaseSettings):
    max_stocks: int = 30
    markets: list[str] = ["KOSPI", "KOSDAQ"]
    min_market_cap_billion: int = 5000
    min_daily_volume: int = 100000
    excluded_sectors: list[str] = ["금융"]


class TradingSettings(BaseSettings):
    mode: str = "NEUTRAL"
    max_concurrent_positions: int = 10
    order_split_threshold: int = 10000000
    order_split_count: int = 3


class AllSettings:
    def __init__(self):
        config_dir = Path(__file__).parent.parent / "config"
        
        with open(config_dir / "settings.yaml", "r") as f:
            settings_yaml = yaml.safe_load(f)
        
        self.app = AppSettings(**settings_yaml.get("app", {}))
        self.kis = KISSettings(**settings_yaml.get("kis", {}))
        self.database = DatabaseSettings(**settings_yaml.get("database", {}))
        self.redis = RedisSettings(**settings_yaml.get("redis", {}))
        self.scheduler = SchedulerSettings(**settings_yaml.get("scheduler", {}))
        self.universe = UniverseSettings(**settings_yaml.get("universe", {}))
        self.trading = TradingSettings(**settings_yaml.get("trading", {}))

    def update_database_url(self, password: str):
        self.database.url = self.database.url.replace("${DB_PASSWORD}", password)


_settings: AllSettings | None = None


def get_settings() -> AllSettings:
    global _settings
    if _settings is None:
        base_settings = Settings()
        _settings = AllSettings()
        _settings.update_database_url(base_settings.db_password)
    return _settings


def get_kis_credentials() -> Settings:
    return Settings()
