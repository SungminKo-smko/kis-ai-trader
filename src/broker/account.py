import logging
from decimal import Decimal
from typing import Optional

from broker.kis_client import get_kis_client
from core.models import Portfolio, Holding

logger = logging.getLogger("account")


class AccountService:
    def __init__(self):
        self._client = get_kis_client()

    def get_balance(self) -> dict:
        return self._client.get_balance()

    def get_portfolio(self) -> Portfolio:
        balance = self._client.get_balance()
        holdings = []
        
        total_value = Decimal(str(balance.get("tot_evlu_amt", 0)))
        cash = Decimal(str(balance.get("cash", 0)))
        
        for item in balance.get("holdings", []):
            holding = Holding(
                symbol=item.get("stk_cd", ""),
                name=item.get("stk_nm", ""),
                quantity=int(item.get("hold_qty", 0)),
                avg_price=Decimal(str(item.get("pchs_avg_pric", 0))),
                current_price=Decimal(str(item.get("cur_pr", 0))),
                market_value=Decimal(str(item.get("evlu_amt", 0))),
                unrealized_pnl=Decimal(str(item.get("evlu_pnl", 0))),
                unrealized_pnl_pct=float(item.get("evlu_pnl_rate", 0)),
            )
            holdings.append(holding)
        
        invested = total_value - cash
        daily_pnl = Decimal(str(balance.get("today_pnl", 0)))
        daily_pnl_pct = float(balance.get("today_pnl_rate", 0))
        
        return Portfolio(
            total_value=total_value,
            cash=cash,
            invested=invested,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            holdings=holdings,
        )

    def get_today_orders(self) -> list[dict]:
        return self._client.get_today_orders()

    def get_today_executions(self) -> list[dict]:
        return self._client.get_today_executions()


_account_service: Optional[AccountService] = None


def get_account_service() -> AccountService:
    global _account_service
    if _account_service is None:
        _account_service = AccountService()
    return _account_service
